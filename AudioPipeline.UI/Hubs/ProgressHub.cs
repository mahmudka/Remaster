using AudioPipeline.Shared.DTOs;
using Microsoft.AspNetCore.SignalR;

namespace AudioPipeline.UI.Hubs;

public class ProgressHub : Hub
{
    public async Task JoinJob(string jobId)
        => await Groups.AddToGroupAsync(Context.ConnectionId, jobId);

    public async Task LeaveJob(string jobId)
        => await Groups.RemoveFromGroupAsync(Context.ConnectionId, jobId);
}

public static class ProgressHubExtensions
{
    public static Task SendProgress(
        this IHubContext<ProgressHub> hub,
        string jobId,
        ProgressDto progress)
        => hub.Clients.Group(jobId).SendAsync("OnProgress", progress);
}
