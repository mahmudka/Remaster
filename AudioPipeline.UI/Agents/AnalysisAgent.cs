using System.Net.Http.Json;
using System.Text.Json;

namespace AudioPipeline.UI.Agents;

public class AnalysisAgent : IAgent
{
    private readonly HttpClient _http;
    private readonly ILogger<AnalysisAgent> _log;
    private readonly string _baseUrl;

    public string Name => "Analysis";

    public AnalysisAgent(IHttpClientFactory factory, IConfiguration config, ILogger<AnalysisAgent> log)
    {
        _http    = factory.CreateClient();
        _log     = log;
        _baseUrl = config["Microservices:AudioUrl"] ?? "http://localhost:8001";
    }

    public async Task<PipelineContext> RunAsync(PipelineContext ctx, CancellationToken ct = default)
    {
        using var form = new MultipartFormDataContent();
        await using var stream = File.OpenRead(ctx.InputFile);
        form.Add(new StreamContent(stream), "file", Path.GetFileName(ctx.InputFile));
        form.Add(new StringContent(ctx.TargetLufs.ToString("F1", System.Globalization.CultureInfo.InvariantCulture)), "target_lufs");

        var resp = await _http.PostAsync($"{_baseUrl}/analyze", form, ct);
        if (!resp.IsSuccessStatusCode)
        {
            var err = await resp.Content.ReadAsStringAsync(ct);
            throw new InvalidOperationException($"analyze failed: {err}");
        }

        var doc = await resp.Content.ReadFromJsonAsync<JsonElement>(cancellationToken: ct);

        ctx.Bpm           = doc.TryGetProperty("bpm",       out var b)  ? (float)b.GetDouble()          : 0;
        ctx.Key           = doc.TryGetProperty("key",       out var k)  ? k.GetString() ?? ""             : "";
        ctx.Genre         = doc.TryGetProperty("genre_hint",out var g)  ? g.GetString() ?? "unknown"      : "unknown";
        ctx.LufsBefore    = doc.TryGetProperty("lufs",      out var lu) ? (float)lu.GetDouble()           : 0;
        ctx.TruePeakBefore= doc.TryGetProperty("true_peak", out var tp) ? (float)tp.GetDouble()           : 0;
        ctx.DrBefore      = doc.TryGetProperty("dr",        out var dr) ? (float)dr.GetDouble()           : 0;
        ctx.LraBefore     = doc.TryGetProperty("lra",       out var lr) ? (float)lr.GetDouble()           : 0;
        ctx.AnalysisJson  = doc.GetRawText();

        if (doc.TryGetProperty("problems", out var probs))
            ctx.ProblemTags = probs.EnumerateArray()
                .Select(p => p.GetString() ?? "")
                .Where(s => s.Length > 0)
                .ToList();

        ctx.LastResult = $"BPM:{ctx.Bpm:F0} LUFS:{ctx.LufsBefore:F1} Проблем:{ctx.ProblemTags.Count}";
        _log.LogInformation("Analysis done: {Result}", ctx.LastResult);
        return ctx;
    }
}
