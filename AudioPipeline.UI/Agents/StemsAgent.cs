using System.Net.Http.Json;
using System.Text.Json;

namespace AudioPipeline.UI.Agents;

public class StemsAgent : IAgent
{
    private readonly HttpClient _http;
    private readonly ILogger<StemsAgent> _log;
    private readonly string _baseUrl;

    public string Name => "Stems";
    public PipelineBlock Block => PipelineBlock.Stems;

    public StemsAgent(IHttpClientFactory factory, IConfiguration config, ILogger<StemsAgent> log)
    {
        _http    = factory.CreateClient();
        _log     = log;
        _baseUrl = config["Microservices:StemsUrl"] ?? "http://localhost:8001";
    }

    public async Task<PipelineContext> RunAsync(PipelineContext ctx, CancellationToken ct = default)
    {
        var resp = await _http.PostAsJsonAsync($"{_baseUrl}/stems_json", new
        {
            file_path   = ctx.InputFile,
            output_path = ctx.OutputPath,
            job_id      = ctx.JobId,
        }, ct);

        if (!resp.IsSuccessStatusCode)
        {
            var err = await resp.Content.ReadAsStringAsync(ct);
            _log.LogWarning("Stems service failed ({Status}): {Err}", resp.StatusCode, err);
            // Fallback: use original file as all stems
            ctx.VocalStem       = ctx.InputFile;
            ctx.BassStem        = ctx.InputFile;
            ctx.DrumsStem       = ctx.InputFile;
            ctx.InstrumentsStem = ctx.InputFile;
            ctx.LastResult = "Stems: fallback (original file)";
            return ctx;
        }

        var doc = await resp.Content.ReadFromJsonAsync<JsonElement>(cancellationToken: ct);

        ctx.VocalStem       = GetStr(doc, "vocals");
        ctx.BassStem        = GetStr(doc, "bass");
        ctx.DrumsStem       = GetStr(doc, "drums");
        ctx.InstrumentsStem = GetStr(doc, "instruments");

        ctx.LastResult = $"Stems: vocals={Path.GetFileName(ctx.VocalStem)}, bass={Path.GetFileName(ctx.BassStem)}";
        _log.LogInformation("Stems done: {Result}", ctx.LastResult);
        return ctx;
    }

    static string? GetStr(JsonElement doc, string prop)
        => doc.TryGetProperty(prop, out var v) ? v.GetString() : null;
}
