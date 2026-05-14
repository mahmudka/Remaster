using System.Net.Http.Json;
using System.Text.Json;

namespace AudioPipeline.UI.Agents;

public class RvcAgent : IAgent
{
    private readonly HttpClient _http;
    private readonly ILogger<RvcAgent> _log;
    private readonly string _baseUrl;

    public string Name => "Rvc";
    public PipelineBlock Block => PipelineBlock.Rvc;

    public RvcAgent(IHttpClientFactory factory, IConfiguration config, ILogger<RvcAgent> log)
    {
        _http    = factory.CreateClient();
        _log     = log;
        _baseUrl = config["Microservices:RvcUrl"] ?? "http://localhost:8004";
    }

    public async Task<PipelineContext> RunAsync(PipelineContext ctx, CancellationToken ct = default)
    {
        if (ctx.VocalStem is null)
        {
            ctx.LastResult = "RVC: no vocal stem, skipped";
            return ctx;
        }

        var resp = await _http.PostAsJsonAsync($"{_baseUrl}/rvc", new
        {
            vocal_wav   = ctx.VocalStem,
            model_path  = ctx.RvcModelPath ?? "",
            index_path  = ctx.RvcIndexPath ?? "",
            output_path = ctx.OutputPath,
        }, ct);

        if (!resp.IsSuccessStatusCode)
        {
            var err = await resp.Content.ReadAsStringAsync(ct);
            _log.LogWarning("RVC failed: {Err}", err);
            ctx.VocalRvc   = ctx.VocalStem;  // fallback: use original vocal
            ctx.LastResult = "RVC: fallback to original vocal";
            return ctx;
        }

        var doc = await resp.Content.ReadFromJsonAsync<JsonElement>(cancellationToken: ct);
        ctx.VocalRvc   = doc.TryGetProperty("output_wav", out var v) ? v.GetString() : ctx.VocalStem;
        ctx.LastResult = "RVC voice conversion complete";
        _log.LogInformation("RVC done");
        return ctx;
    }
}
