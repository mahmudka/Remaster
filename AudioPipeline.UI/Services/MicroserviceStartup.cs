using System.Diagnostics;

namespace AudioPipeline.UI.Services;

public class MicroserviceStartup : IHostedService
{
    private readonly List<Process> _procs = new();
    private readonly ILogger<MicroserviceStartup> _log;
    private readonly string _servicesRoot;

    public MicroserviceStartup(ILogger<MicroserviceStartup> log, IConfiguration config)
    {
        _log          = log;
        _servicesRoot = config["ServicesRoot"] ?? FindServicesRoot();
    }

    public async Task StartAsync(CancellationToken ct)
    {
        if (!Directory.Exists(_servicesRoot))
        {
            _log.LogWarning("Services directory not found: {Dir}. Skipping autostart.", _servicesRoot);
            return;
        }

        KillPortOwner(8001);
        KillPortOwner(8002);
        KillPortOwner(8003);
        KillPortOwner(8004);

        Launch("python_stems", "python -m uvicorn main:app --port 8001 --host 0.0.0.0");
        Launch("python_mix",   "python -m uvicorn main:app --port 8002 --host 0.0.0.0");
        Launch("python_rvc",   "python -m uvicorn main:app --port 8004 --host 0.0.0.0");
        LaunchVstStub();

        // Give services time to initialise
        await Task.Delay(3000, ct);
        _log.LogInformation("Microservices started ({Count} processes)", _procs.Count);
    }

    public Task StopAsync(CancellationToken ct)
    {
        foreach (var p in _procs)
        {
            try { p.Kill(entireProcessTree: true); }
            catch (Exception ex) { _log.LogWarning("Kill failed: {Msg}", ex.Message); }
        }
        _procs.Clear();
        return Task.CompletedTask;
    }

    private void Launch(string serviceDir, string command)
    {
        var dir = Path.Combine(_servicesRoot, serviceDir);
        if (!Directory.Exists(dir))
        {
            _log.LogWarning("Service dir missing: {Dir}", dir);
            return;
        }

        var parts = command.Split(' ', 2);
        var psi = new ProcessStartInfo(parts[0], parts.Length > 1 ? parts[1] : "")
        {
            WorkingDirectory       = dir,
            UseShellExecute        = false,
            RedirectStandardOutput = false,
            RedirectStandardError  = false,
            CreateNoWindow         = true,
        };

        try
        {
            var proc = Process.Start(psi);
            if (proc is not null)
            {
                _procs.Add(proc);
                _log.LogInformation("Started {Service} (pid {Pid})", serviceDir, proc.Id);
            }
        }
        catch (Exception ex)
        {
            _log.LogWarning("Failed to start {Service}: {Msg}", serviceDir, ex.Message);
        }
    }

    private void LaunchVstStub()
    {
        var stubPath = Path.Combine(_servicesRoot, "cpp_vst", "stub_server.py");
        if (!File.Exists(stubPath))
        {
            _log.LogWarning("VST stub not found: {Path}", stubPath);
            return;
        }

        var psi = new ProcessStartInfo("python", $"\"{stubPath}\"")
        {
            WorkingDirectory = Path.GetDirectoryName(stubPath)!,
            UseShellExecute  = false,
            CreateNoWindow   = true,
        };

        try
        {
            var proc = Process.Start(psi);
            if (proc is not null)
            {
                _procs.Add(proc);
                _log.LogInformation("Started VST stub (pid {Pid})", proc.Id);
            }
        }
        catch (Exception ex)
        {
            _log.LogWarning("Failed to start VST stub: {Msg}", ex.Message);
        }
    }

    private void KillPortOwner(int port)
    {
        try
        {
            var psi = new ProcessStartInfo("cmd",
                $"/c for /f \"tokens=5\" %a in ('netstat -aon ^| findstr :{port} ^| findstr LISTENING') do taskkill /F /PID %a")
            {
                UseShellExecute        = false,
                RedirectStandardOutput = false,
                RedirectStandardError  = false,
                CreateNoWindow         = true,
            };
            using var p = Process.Start(psi);
            p?.WaitForExit(3000);
        }
        catch (Exception ex)
        {
            _log.LogDebug("KillPortOwner({Port}): {Msg}", port, ex.Message);
        }
    }

    // Walk up from the app binary until a 'services' sibling is found
    private static string FindServicesRoot()
    {
        var dir = AppContext.BaseDirectory;
        for (int i = 0; i < 6; i++)
        {
            var candidate = Path.Combine(dir, "services");
            if (Directory.Exists(candidate)) return candidate;
            dir = Path.GetDirectoryName(dir) ?? dir;
        }
        return Path.Combine(AppContext.BaseDirectory, "services");
    }
}
