using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using AudioPipeline.Shared.Data;
using Microsoft.EntityFrameworkCore;

namespace AudioPipeline.UI.Agents;

public class KnowledgeAgent : IAgent
{
    private readonly HttpClient _http;
    private readonly AudioPipelineContext _db;
    private readonly IConfiguration _config;
    private readonly ILogger<KnowledgeAgent> _log;

    public string Name => "Knowledge";
    public PipelineBlock Block => PipelineBlock.Knowledge;

    public KnowledgeAgent(
        IHttpClientFactory factory,
        AudioPipelineContext db,
        IConfiguration config,
        ILogger<KnowledgeAgent> log)
    {
        _http   = factory.CreateClient();
        _db     = db;
        _config = config;
        _log    = log;
    }

    public async Task<PipelineContext> RunAsync(PipelineContext ctx, CancellationToken ct = default)
    {
        var genre = ctx.Genre.Length > 0 ? ctx.Genre : "unknown";

        // 1. Get rules from DB
        var rules = await _db.GetBestParameters(genre).ToListAsync(ct);

        // 2. Try Claude API for mix plan
        var apiKey = _config["Claude:ApiKey"];
        if (!string.IsNullOrEmpty(apiKey) && apiKey != "YOUR_API_KEY")
        {
            try
            {
                ctx.MixPlan = await GenerateMixPlan(ctx, rules, apiKey, ct);
                ctx.LastResult = $"Mix plan generated via Claude ({ctx.MixPlan.Tracks.Count} tracks)";
                return ctx;
            }
            catch (Exception ex)
            {
                _log.LogWarning("Claude API failed, using default plan: {Err}", ex.Message);
            }
        }

        // 3. Fallback: default plan from DB rules
        ctx.MixPlan    = BuildDefaultPlan(rules);
        ctx.LastResult = $"Mix plan: default ({rules.Count} rules from DB)";
        _log.LogInformation("Knowledge done (default plan)");
        return ctx;
    }

    private async Task<MixPlan> GenerateMixPlan(
        PipelineContext ctx,
        List<BestParameterResult> rules,
        string apiKey,
        CancellationToken ct)
    {
        var model   = _config["Claude:Models:Balanced"] ?? "claude-sonnet-4-6";
        var rulesJson = JsonSerializer.Serialize(rules.Take(30).Select(r => new
        {
            r.Parameter, r.Value, r.Unit, r.Rationale, r.Source
        }));

        var schema = """
            {"Tracks":[{"Track":"vocals","Eq":[{"Frequency":1000,"Gain":2,"Q":1,"Type":"peak"}],
            "Comp":{"Threshold":-20,"Ratio":4,"Attack":10,"Release":100,"MakeupGain":2},
            "Gain":0,"Pan":0,"Rationale":"...","BookSource":"..."}],
            "Bus":{"Compression":{},"Eq":[]},"Reverb":{"RoomSize":0.5,"Damping":0.5,"WetLevel":0.15,"DryLevel":0.85,"PreDelay":20},
            "Delay":{"Time":250,"Feedback":0.3,"WetLevel":0.2},"Sources":["Book chapter"]}
            """;

        var userPrompt = $"Track: BPM={ctx.Bpm:F0}, Key={ctx.Key}, Genre={ctx.Genre}\n" +
                         $"Knowledge rules: {rulesJson}\n\n" +
                         "Create a mix plan for stems: vocals, bass, drums, instruments.\n" +
                         "Reverb and delay go ONLY on the assembled mix, never on individual stems.\n" +
                         $"Respond ONLY with valid JSON matching this schema:\n{schema}";

        using var req = new HttpRequestMessage(HttpMethod.Post, "https://api.anthropic.com/v1/messages");
        req.Headers.Add("x-api-key", apiKey);
        req.Headers.Add("anthropic-version", "2023-06-01");

        var body = new
        {
            model,
            max_tokens = 2000,
            system = "You are a professional mixing engineer. Respond ONLY with valid JSON.",
            messages = new[] { new { role = "user", content = userPrompt } }
        };
        req.Content = new StringContent(JsonSerializer.Serialize(body), Encoding.UTF8, "application/json");

        var resp = await _http.SendAsync(req, ct);
        resp.EnsureSuccessStatusCode();

        var doc    = await resp.Content.ReadFromJsonAsync<JsonElement>(cancellationToken: ct);
        var text   = doc.GetProperty("content")[0].GetProperty("text").GetString() ?? "{}";
        return JsonSerializer.Deserialize<MixPlan>(text, new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true
        }) ?? BuildDefaultPlan(new List<BestParameterResult>());
    }

    private static MixPlan BuildDefaultPlan(List<BestParameterResult> rules)
    {
        var tracks = new[] { "vocals", "bass", "drums", "instruments" }.Select(name =>
        {
            var trackRules = rules.Where(r =>
                r.Parameter.Contains(name, StringComparison.OrdinalIgnoreCase)).ToList();

            return new TrackRecommendation
            {
                Track      = name,
                Gain       = name == "vocals" ? 0 : -2,
                Pan        = 0,
                Comp       = new CompSettings { Threshold = -20, Ratio = 4, Attack = 10, Release = 100 },
                Rationale  = trackRules.FirstOrDefault()?.Rationale ?? "Default settings",
                BookSource = trackRules.FirstOrDefault()?.Source ?? "Default",
            };
        }).ToList();

        return new MixPlan
        {
            Tracks  = tracks,
            Reverb  = new ReverbSettings(),
            Delay   = new DelaySettings(),
            Sources = rules.Select(r => r.Source ?? "").Where(s => s.Length > 0).Distinct().ToList(),
        };
    }
}
