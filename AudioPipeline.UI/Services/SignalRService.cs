using AudioPipeline.Shared.DTOs;
using Microsoft.AspNetCore.SignalR.Client;

namespace AudioPipeline.UI.Services;

public class SignalRService : IAsyncDisposable
{
    private HubConnection? _hub;
    private readonly IConfiguration _config;

    public event Action<ProgressDto>? OnProgress;

    public SignalRService(IConfiguration config)
    {
        _config = config;
    }

    public async Task ConnectAsync()
    {
        var url = _config["Microservices:HubUrl"] ?? "http://localhost:5000/progressHub";
        _hub = new HubConnectionBuilder()
            .WithUrl(url)
            .WithAutomaticReconnect()
            .Build();

        _hub.On<ProgressDto>("OnProgress", dto => OnProgress?.Invoke(dto));

        await _hub.StartAsync();
    }

    public async Task JoinJobAsync(string jobId)
    {
        if (_hub?.State == HubConnectionState.Connected)
            await _hub.SendAsync("JoinJob", jobId);
    }

    public async Task LeaveJobAsync(string jobId)
    {
        if (_hub?.State == HubConnectionState.Connected)
            await _hub.SendAsync("LeaveJob", jobId);
    }

    public async ValueTask DisposeAsync()
    {
        if (_hub is not null)
            await _hub.DisposeAsync();
    }
}
