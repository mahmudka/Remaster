using AudioPipeline.Shared.Models;
using System.Net.Http.Json;
using System.Text.Json;

namespace AudioPipeline.UI.Agents;

public class PlanAgent : IAgent
{
    private readonly HttpClient _http;
    private readonly ILogger<PlanAgent> _log;
    private readonly string _baseUrl;

    public string Name => "Plan";

    public PlanAgent(IHttpClientFactory factory, IConfiguration config, ILogger<PlanAgent> log)
    {
        _http    = factory.CreateClient();
        _log     = log;
        _baseUrl = config["Microservices:AudioUrl"] ?? "http://localhost:8001";
    }

    public async Task<PipelineContext> RunAsync(PipelineContext ctx, CancellationToken ct = default)
    {
        var resp = await _http.PostAsJsonAsync($"{_baseUrl}/plan", new
        {
            tags        = ctx.ProblemTags,
            genre       = ctx.Genre,
            target_lufs = ctx.TargetLufs,
        }, ct);

        if (!resp.IsSuccessStatusCode)
        {
            var err = await resp.Content.ReadAsStringAsync(ct);
            throw new InvalidOperationException($"plan failed: {err}");
        }

        ctx.Plan = await resp.Content
            .ReadFromJsonAsync<MasteringPlan>(
                new JsonSerializerOptions { PropertyNameCaseInsensitive = true },
                cancellationToken: ct)
            ?? new MasteringPlan();

        ctx.LastResult = $"Plan: {ctx.Plan.AppliedTags.Count} проблем → {ctx.Plan.Eq.Count} EQ полос";
        _log.LogInformation("Plan done: {Result}", ctx.LastResult);
        return ctx;
    }
}
