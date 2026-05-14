using System.Net.Http.Json;
using System.Text.Json;

namespace AudioPipeline.UI.Agents;

public class MasterAgent : IAgent
{
    private readonly HttpClient _http;
    private readonly ILogger<MasterAgent> _log;
    private readonly string _baseUrl;

    public string Name => "Master";
    public PipelineBlock Block => PipelineBlock.Master;

    public MasterAgent(IHttpClientFactory factory, IConfiguration config, ILogger<MasterAgent> log)
    {
        _http    = factory.CreateClient();
        _log     = log;
        _baseUrl = config["Microservices:MixUrl"] ?? "http://localhost:8002";
    }

    public async Task<PipelineContext> RunAsync(PipelineContext ctx, CancellationToken ct = default)
    {
        if (ctx.MixFile is null)
            throw new InvalidOperationException("No mix file available for mastering");

        var resp = await _http.PostAsJsonAsync($"{_baseUrl}/master_json", new
        {
            mix_wav     = ctx.MixFile,
            output_path = ctx.OutputPath,
            job_id      = ctx.JobId,
        }, ct);

        if (!resp.IsSuccessStatusCode)
        {
            var err = await resp.Content.ReadAsStringAsync(ct);
            throw new InvalidOperationException($"Master failed: {err}");
        }

        var doc = await resp.Content.ReadFromJsonAsync<JsonElement>(cancellationToken: ct);
        ctx.MasterWav  = doc.TryGetProperty("master_wav", out var w) ? w.GetString() : null;
        ctx.MasterMp3  = doc.TryGetProperty("master_mp3", out var p) ? p.GetString() : null;
        ctx.LastResult = $"Master complete: {Path.GetFileName(ctx.MasterWav)}";
        _log.LogInformation("Master done: {File}", ctx.MasterWav);
        return ctx;
    }
}
