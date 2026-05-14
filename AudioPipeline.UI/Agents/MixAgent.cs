using System.Net.Http.Json;
using System.Text.Json;

namespace AudioPipeline.UI.Agents;

public class MixAgent : IAgent
{
    private readonly HttpClient _http;
    private readonly ILogger<MixAgent> _log;
    private readonly string _baseUrl;

    public string Name => "Mix";
    public PipelineBlock Block => PipelineBlock.Mix;

    public MixAgent(IHttpClientFactory factory, IConfiguration config, ILogger<MixAgent> log)
    {
        _http    = factory.CreateClient();
        _log     = log;
        _baseUrl = config["Microservices:MixUrl"] ?? "http://localhost:8002";
    }

    public async Task<PipelineContext> RunAsync(PipelineContext ctx, CancellationToken ct = default)
    {
        // Use VST-rendered or dry stems
        var vocals      = ctx.VocalRvc       ?? ctx.VocalStem       ?? ctx.InputFile;
        var bass        = ctx.BassVst        ?? ctx.BassStem        ?? ctx.InputFile;
        var drums       = ctx.DrumsVst       ?? ctx.DrumsStem       ?? ctx.InputFile;
        var instruments = ctx.InstrumentsVst ?? ctx.InstrumentsStem ?? ctx.InputFile;

        var resp = await _http.PostAsJsonAsync($"{_baseUrl}/mix_json", new
        {
            vocals,
            bass,
            drums,
            instruments,
            mix_plan       = ctx.MixPlan,
            output_path    = ctx.OutputPath,
            reference_file = ctx.ReferenceFile,
            job_id         = ctx.JobId,
        }, ct);

        if (!resp.IsSuccessStatusCode)
        {
            var err = await resp.Content.ReadAsStringAsync(ct);
            throw new InvalidOperationException($"Mix failed: {err}");
        }

        var doc = await resp.Content.ReadFromJsonAsync<JsonElement>(cancellationToken: ct);
        ctx.MixFile    = doc.TryGetProperty("mix_wav", out var m) ? m.GetString() : null;
        ctx.LastResult = $"Mix complete: {Path.GetFileName(ctx.MixFile)}";
        _log.LogInformation("Mix done: {File}", ctx.MixFile);
        return ctx;
    }
}
