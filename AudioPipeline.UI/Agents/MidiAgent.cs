using System.Net.Http.Json;
using System.Text.Json;

namespace AudioPipeline.UI.Agents;

public class MidiAgent : IAgent
{
    private readonly HttpClient _http;
    private readonly ILogger<MidiAgent> _log;
    private readonly string _baseUrl;

    public string Name => "Midi";
    public PipelineBlock Block => PipelineBlock.Midi;

    public MidiAgent(IHttpClientFactory factory, IConfiguration config, ILogger<MidiAgent> log)
    {
        _http    = factory.CreateClient();
        _log     = log;
        _baseUrl = config["Microservices:StemsUrl"] ?? "http://localhost:8001";
    }

    public async Task<PipelineContext> RunAsync(PipelineContext ctx, CancellationToken ct = default)
    {
        var resp = await _http.PostAsJsonAsync($"{_baseUrl}/midi_json", new
        {
            bass_stem        = ctx.BassStem,
            drums_stem       = ctx.DrumsStem,
            instruments_stem = ctx.InstrumentsStem,
            output_path      = ctx.OutputPath,
            job_id           = ctx.JobId,
        }, ct);

        if (!resp.IsSuccessStatusCode)
        {
            var err = await resp.Content.ReadAsStringAsync(ct);
            _log.LogWarning("MIDI service failed: {Err}", err);
            ctx.LastResult = "MIDI: skipped (service unavailable)";
            return ctx;
        }

        var doc = await resp.Content.ReadFromJsonAsync<JsonElement>(cancellationToken: ct);

        ctx.BassMidi        = GetStr(doc, "bass_midi");
        ctx.DrumsMidi       = GetStr(doc, "drums_midi");
        ctx.InstrumentsMidi = GetStr(doc, "instruments_midi");

        ctx.LastResult = "MIDI transcription complete";
        _log.LogInformation("MIDI done");
        return ctx;
    }

    static string? GetStr(JsonElement doc, string prop)
        => doc.TryGetProperty(prop, out var v) ? v.GetString() : null;
}
