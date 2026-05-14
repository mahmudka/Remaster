using System.Net.Http.Json;
using System.Text.Json;

namespace AudioPipeline.UI.Agents;

public class VstAgent : IAgent
{
    private readonly HttpClient _http;
    private readonly ILogger<VstAgent> _log;
    private readonly string _baseUrl;

    public string Name => "Vst";
    public PipelineBlock Block => PipelineBlock.Vst;

    public VstAgent(IHttpClientFactory factory, IConfiguration config, ILogger<VstAgent> log)
    {
        _http    = factory.CreateClient();
        _log     = log;
        _baseUrl = config["Microservices:VstUrl"] ?? "http://localhost:8003";
    }

    public async Task<PipelineContext> RunAsync(PipelineContext ctx, CancellationToken ct = default)
    {
        var resp = await _http.PostAsJsonAsync($"{_baseUrl}/render", new
        {
            bass_midi        = ctx.BassMidi,
            drums_midi       = ctx.DrumsMidi,
            instruments_midi = ctx.InstrumentsMidi,
            output_path      = ctx.OutputPath,
            bpm              = ctx.Bpm,
        }, ct);

        if (!resp.IsSuccessStatusCode)
        {
            var err = await resp.Content.ReadAsStringAsync(ct);
            _log.LogWarning("VST render failed: {Err}", err);
            // Fallback to dry stems
            ctx.BassVst        = ctx.BassStem;
            ctx.DrumsVst       = ctx.DrumsStem;
            ctx.InstrumentsVst = ctx.InstrumentsStem;
            ctx.LastResult = "VST: fallback to dry stems";
            return ctx;
        }

        var doc = await resp.Content.ReadFromJsonAsync<JsonElement>(cancellationToken: ct);

        ctx.BassVst        = GetStr(doc, "bass_wav");
        ctx.DrumsVst       = GetStr(doc, "drums_wav");
        ctx.InstrumentsVst = GetStr(doc, "instruments_wav");

        ctx.LastResult = "VST render complete";
        _log.LogInformation("VST done");
        return ctx;
    }

    static string? GetStr(JsonElement doc, string prop)
        => doc.TryGetProperty(prop, out var v) ? v.GetString() : null;
}
