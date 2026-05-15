using System.Net.Http.Json;
using System.Text.Json;

namespace AudioPipeline.UI.Agents;

public record MasterResult(
    string OutputWav,
    string ReportJson,
    float  LufsAfter,
    float  TruePeakAfter,
    float  DrAfter,
    float  LraAfter,
    string AnalysisAfterJson);

public class MasteringAgent : IAgent
{
    private readonly HttpClient _http;
    private readonly ILogger<MasteringAgent> _log;
    private readonly string _baseUrl;

    public string Name => "Mastering";

    public MasteringAgent(IHttpClientFactory factory, IConfiguration config, ILogger<MasteringAgent> log)
    {
        _http    = factory.CreateClient();
        _log     = log;
        _baseUrl = config["Microservices:AudioUrl"] ?? "http://localhost:8001";
    }

    public async Task<PipelineContext> RunAsync(PipelineContext ctx, CancellationToken ct = default)
    {
        var outputWav = Path.Combine(ctx.OutputPath, "master.wav");

        var resp = await _http.PostAsJsonAsync($"{_baseUrl}/master", new
        {
            input_path  = ctx.InputFile,
            plan        = ctx.Plan,
            output_path = outputWav,
        }, ct);

        if (!resp.IsSuccessStatusCode)
        {
            var err = await resp.Content.ReadAsStringAsync(ct);
            throw new InvalidOperationException($"master failed: {err}");
        }

        var doc = await resp.Content.ReadFromJsonAsync<JsonElement>(cancellationToken: ct);

        ctx.OutputWav         = doc.TryGetProperty("output_wav",   out var ow)  ? ow.GetString()  ?? outputWav : outputWav;
        ctx.ReportJson        = doc.TryGetProperty("report",       out var rp)  ? rp.GetRawText() : "{}";
        ctx.LufsAfter         = doc.TryGetProperty("lufs_final",   out var lf)  ? lf.GetSingle()  : 0;
        ctx.TruePeakAfter     = doc.TryGetProperty("true_peak_final", out var tf) ? tf.GetSingle() : 0;
        ctx.AnalysisAfterJson = doc.TryGetProperty("analysis_after", out var aa) ? aa.GetRawText() : "";

        ctx.LastResult = $"LUFS: {ctx.LufsBefore:F1} → {ctx.LufsAfter:F1} | TP: {ctx.TruePeakAfter:F1} дБ";
        _log.LogInformation("Mastering done: {Result}", ctx.LastResult);
        return ctx;
    }
}
