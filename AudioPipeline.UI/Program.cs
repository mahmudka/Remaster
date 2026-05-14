using AudioPipeline.Shared.Data;
using AudioPipeline.UI.Agents;
using AudioPipeline.UI.Components;
using AudioPipeline.UI.Hubs;
using AudioPipeline.UI.Services;
using Microsoft.EntityFrameworkCore;
using MudBlazor.Services;

var builder = WebApplication.CreateBuilder(args);

// Razor + Blazor Server
builder.Services.AddRazorComponents()
    .AddInteractiveServerComponents();

// MudBlazor
builder.Services.AddMudServices();

// SignalR
builder.Services.AddSignalR();

// EF Core
builder.Services.AddDbContext<AudioPipelineContext>(options =>
    options.UseSqlServer(
        builder.Configuration.GetConnectionString("DefaultConnection")
        ?? AudioPipelineContext.DefaultConnectionString));

// HttpClient for microservice calls
builder.Services.AddHttpClient<PipelineService>(client =>
{
    client.Timeout = TimeSpan.FromMinutes(10);
});
builder.Services.AddHttpClient(); // default factory for agents

// App services
builder.Services.AddScoped<PipelineService>();
builder.Services.AddScoped<SignalRService>();

// Agents (scoped — get DB from scope inside OrchestratorService)
builder.Services.AddScoped<AnalysisAgent>();
builder.Services.AddScoped<StemsAgent>();
builder.Services.AddScoped<MidiAgent>();
builder.Services.AddScoped<VstAgent>();
builder.Services.AddScoped<RvcAgent>();
builder.Services.AddScoped<KnowledgeAgent>();
builder.Services.AddScoped<MixAgent>();
builder.Services.AddScoped<MasterAgent>();

// Orchestrator — singleton, manages background tasks
builder.Services.AddSingleton<OrchestratorService>();

// Microservice autostart
builder.Services.AddHostedService<MicroserviceStartup>();

var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error", createScopeForErrors: true);
    app.UseHsts();
}

app.UseHttpsRedirection();
app.UseStaticFiles();
app.UseAntiforgery();

// SignalR hub
app.MapHub<ProgressHub>("/progressHub");

// Audio file streaming endpoint
app.MapGet("/audio", (string path, HttpContext ctx) =>
{
    if (!File.Exists(path))
        return Results.NotFound();
    var mime = path.EndsWith(".mp3") ? "audio/mpeg" : "audio/wav";
    return Results.File(path, mime, enableRangeProcessing: true);
});

app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode();

app.Run();
