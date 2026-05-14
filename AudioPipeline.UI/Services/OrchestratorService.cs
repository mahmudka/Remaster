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

    // Ordered dependency chain
    private static readonly Dictionary<PipelineBlock, PipelineBlock[]> Deps = new()
    {
        [PipelineBlock.Stems]     = new[] { PipelineBlock.Analysis },
        [PipelineBlock.Knowledge] = new[] { PipelineBlock.Analysis },
        [PipelineBlock.Midi]      = new[] { PipelineBlock.Stems },
        [PipelineBlock.Vst]       = new[] { PipelineBlock.Midi },
        [PipelineBlock.Rvc]       = new[] { PipelineBlock.Stems },
        [PipelineBlock.Mix]       = new[] { PipelineBlock.Knowledge },
        [PipelineBlock.Master]    = new[] { PipelineBlock.Mix },
    };

    public OrchestratorService(
        IServiceScopeFactory scopes,
        IHubContext<ProgressHub> hub,
        ILogger<OrchestratorService> log)
    {
        _scopes = scopes;
        _hub    = hub;
        _log    = log;
    }

    public Task RunPipelineAsync(
        string jobId, string inputFile, string outputPath,
        string? referenceFile, List<string> selectedBlocks)
    {
        return Task.Run(async () =>
        {
            try
            {
                await ExecuteAsync(jobId, inputFile, outputPath, referenceFile, selectedBlocks);
            }
            catch (Exception ex)
            {
                _log.LogError(ex, "Pipeline failed for job {JobId}", jobId);
                await PushAsync(jobId, "Pipeline", "error", ex.Message, 100);
            }
        });
    }

    private async Task ExecuteAsync(
        string jobId, string inputFile, string outputPath,
        string? referenceFile, List<string> selectedBlockNames)
    {
        using var scope = _scopes.CreateScope();
        var sp = scope.ServiceProvider;
        var db = sp.GetRequiredService<AudioPipelineContext>();

        // Load default RVC voice model if available
        var defaultModel = await db.VoiceModels.FirstOrDefaultAsync(m => m.IsDefault);

        var ctx = new PipelineContext
        {
            JobId        = jobId,
            InputFile    = inputFile,
            OutputPath   = outputPath,
            ReferenceFile = referenceFile,
            RvcModelPath = defaultModel?.ModelPath,
            RvcIndexPath = defaultModel?.IndexPath,
        };

        var selected = selectedBlockNames
            .Select(n => Enum.TryParse<PipelineBlock>(n, out var e) ? (PipelineBlock?)e : null)
            .Where(e => e.HasValue).Select(e => e!.Value).ToList();

        var ordered = ResolveDependencies(selected);
        var agents  = BuildAgents(sp);

        for (int i = 0; i < ordered.Count; i++)
        {
            var block = ordered[i];
            if (!agents.TryGetValue(block, out var agent)) continue;

            var pct = i * 100 / ordered.Count;
            await PushAsync(jobId, agent.Name, "running", $"Запуск {agent.Name}...", pct);

            try
            {
                ctx = await agent.RunAsync(ctx);
                ctx.BlocksRun.Add(agent.Name);
                pct = (i + 1) * 100 / ordered.Count;
                await PushAsync(jobId, agent.Name, "done", ctx.LastResult, pct);
            }
            catch (Exception ex)
            {
                ctx.Errors.Add($"{agent.Name}: {ex.Message}");
                _log.LogError(ex, "Agent {Agent} failed", agent.Name);
                await PushAsync(jobId, agent.Name, "error", ex.Message, pct);
            }
        }

        // Persist final session state
        var session = await db.MixSessions.FirstOrDefaultAsync(s => s.JobId == jobId);
        if (session is not null)
        {
            session.Status      = ctx.Errors.Count == 0 ? "Done" : "Failed";
            session.Genre       = ctx.Genre;
            session.Bpm         = ctx.Bpm;
            session.Key         = ctx.Key;
            session.CompletedAt = DateTime.UtcNow;
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

    private static List<PipelineBlock> ResolveDependencies(List<PipelineBlock> selected)
    {
        var resolved = new HashSet<PipelineBlock>();
        var ordered  = new List<PipelineBlock>();

        void Add(PipelineBlock block)
        {
            if (resolved.Contains(block)) return;
            if (Deps.TryGetValue(block, out var deps))
                foreach (var dep in deps) Add(dep);
            resolved.Add(block);
            ordered.Add(block);
        }

        foreach (var b in selected) Add(b);
        return ordered;
    }

    private static Dictionary<PipelineBlock, IAgent> BuildAgents(IServiceProvider sp)
        => new()
        {
            [PipelineBlock.Analysis]  = sp.GetRequiredService<AnalysisAgent>(),
            [PipelineBlock.Stems]     = sp.GetRequiredService<StemsAgent>(),
            [PipelineBlock.Midi]      = sp.GetRequiredService<MidiAgent>(),
            [PipelineBlock.Vst]       = sp.GetRequiredService<VstAgent>(),
            [PipelineBlock.Rvc]       = sp.GetRequiredService<RvcAgent>(),
            [PipelineBlock.Knowledge] = sp.GetRequiredService<KnowledgeAgent>(),
            [PipelineBlock.Mix]       = sp.GetRequiredService<MixAgent>(),
            [PipelineBlock.Master]    = sp.GetRequiredService<MasterAgent>(),
        };
}
