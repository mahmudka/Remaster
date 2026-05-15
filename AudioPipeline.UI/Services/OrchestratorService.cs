using AudioPipeline.Shared.Data;
using AudioPipeline.Shared.DTOs;
using AudioPipeline.UI.Agents;
using AudioPipeline.UI.Hubs;
using Microsoft.AspNetCore.SignalR;
using Microsoft.EntityFrameworkCore;

namespace AudioPipeline.UI.Services;

public class OrchestratorService
{
    private readonly IServiceScopeFactory _scopes;
    private readonly IHubContext<ProgressHub> _hub;
    private readonly ILogger<OrchestratorService> _log;

    public OrchestratorService(
        IServiceScopeFactory scopes,
        IHubContext<ProgressHub> hub,
        ILogger<OrchestratorService> log)
    {
        _scopes = scopes;
        _hub    = hub;
        _log    = log;
    }

    public Task RunPipelineAsync(string jobId, string inputFile, string outputPath, float targetLufs = -14f)
    {
        return Task.Run(async () =>
        {
            try   { await ExecuteAsync(jobId, inputFile, outputPath, targetLufs); }
            catch (Exception ex)
            {
                _log.LogError(ex, "Pipeline failed for job {JobId}", jobId);
                await PushAsync(jobId, "Pipeline", "error", ex.Message, 100);
            }
        });
    }

    private async Task ExecuteAsync(string jobId, string inputFile, string outputPath, float targetLufs)
    {
        using var scope = _scopes.CreateScope();
        var sp = scope.ServiceProvider;
        var db = sp.GetRequiredService<AudioPipelineContext>();

        var ctx = new PipelineContext
        {
            JobId      = jobId,
            InputFile  = inputFile,
            OutputPath = outputPath,
            TargetLufs = targetLufs,
        };

        IAgent[] pipeline =
        [
            sp.GetRequiredService<AnalysisAgent>(),
            sp.GetRequiredService<PlanAgent>(),
            sp.GetRequiredService<MasteringAgent>(),
        ];

        for (int i = 0; i < pipeline.Length; i++)
        {
            var agent = pipeline[i];
            var pct   = i * 100 / pipeline.Length;
            await PushAsync(jobId, agent.Name, "running", $"Запуск {agent.Name}...", pct);

            try
            {
                ctx = await agent.RunAsync(ctx);
                pct = Math.Min((i + 1) * 100 / pipeline.Length, 99);
                await PushAsync(jobId, agent.Name, "done", ctx.LastResult, pct);
            }
            catch (Exception ex)
            {
                ctx.Errors.Add($"{agent.Name}: {ex.Message}");
                _log.LogError(ex, "Agent {Agent} failed", agent.Name);
                await PushAsync(jobId, agent.Name, "error", ex.Message, pct);
                break;
            }
        }

        var session = await db.MixSessions.FirstOrDefaultAsync(s => s.JobId == jobId);
        if (session is not null)
        {
            session.Status             = ctx.Errors.Count == 0 ? "Done" : "Failed";
            session.Genre              = ctx.Genre;
            session.Bpm                = ctx.Bpm;
            session.Key                = ctx.Key;
            session.CompletedAt        = DateTime.UtcNow;
            session.AnalysisBeforeJson = ctx.AnalysisJson;
            session.AnalysisAfterJson  = ctx.AnalysisAfterJson;
            session.PlanJson           = System.Text.Json.JsonSerializer.Serialize(ctx.Plan);
            session.ProblemsDetected   = string.Join(",", ctx.ProblemTags);
            await db.SaveChangesAsync();
        }

        await PushAsync(jobId, "Pipeline", "done",
            ctx.Errors.Count == 0 ? "Обработка завершена" : $"Завершено с ошибками: {ctx.Errors.Count}",
            100);
    }

    private Task PushAsync(string jobId, string block, string status, string message, int pct)
        => _hub.SendProgress(jobId, new ProgressDto
        {
            JobId           = jobId,
            Block           = block,
            Status          = status,
            Message         = message,
            ProgressPercent = pct,
            Timestamp       = DateTime.UtcNow,
        });
}
