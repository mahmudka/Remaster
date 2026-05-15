namespace AudioPipeline.UI.Agents;

public interface IAgent
{
    string Name { get; }
    Task<PipelineContext> RunAsync(PipelineContext ctx, CancellationToken ct = default);
}
