using System.Net.Http.Json;
using System.Text.Json;

namespace AudioPipeline.UI.Agents;

public class AnalysisAgent : IAgent
{
    private readonly HttpClient _http;
    private readonly ILogger<AnalysisAgent> _log;
    private readonly string _baseUrl;

    public string Name => "Analysis";
    public PipelineBlock Block => PipelineBlock.Analysis;

    public AnalysisAgent(IHttpClientFactory factory, IConfiguration config, ILogger<AnalysisAgent> log)
    {
        _http    = factory.CreateClient();
        _log     = log;
        _baseUrl = config["Microservices:StemsUrl"] ?? "http://localhost:8001";
    }

    public async Task<PipelineContext> RunAsync(PipelineContext ctx, CancellationToken ct = default)
    {
        var resp = await _http.PostAsJsonAsync($"{_baseUrl}/analyze_local",
            new { file_path = ctx.InputFile, job_id = ctx.JobId }, ct);

        if (!resp.IsSuccessStatusCode)
        {
            var err = await resp.Content.ReadAsStringAsync(ct);
            throw new InvalidOperationException($"analyze failed: {err}");
        }

        var doc = await resp.Content.ReadFromJsonAsync<JsonElement>(cancellationToken: ct);

        ctx.Bpm   = doc.TryGetProperty("bpm", out var b) ? b.GetSingle() : 0;
        ctx.Key   = doc.TryGetProperty("key", out var k) ? k.GetString() ?? "" : "";
        ctx.Genre = doc.TryGetProperty("genre", out var g) ? g.GetString() ?? "unknown" : "unknown";

        if (doc.TryGetProperty("frequency_map", out var fm))
            ctx.FrequencyMap = fm.GetRawText();
        if (doc.TryGetProperty("dynamics", out var dyn))
            ctx.DynamicsProfile = dyn.GetRawText();
        if (doc.TryGetProperty("stereo", out var st))
            ctx.StereoProfile = st.GetRawText();

        ctx.LastResult = $"BPM: {ctx.Bpm:F0}, Key: {ctx.Key}, Genre: {ctx.Genre}";
        _log.LogInformation("Analysis done: {Result}", ctx.LastResult);
        return ctx;
    }
}
