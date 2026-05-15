using AudioPipeline.Shared.Models;

namespace AudioPipeline.UI.Agents;

public class PipelineContext
{
    public string        InputFile          { get; set; } = "";
    public string        OutputPath         { get; set; } = "";
    public float         TargetLufs         { get; set; } = -14f;

    // Analysis — before
    public float         LufsBefore         { get; set; }
    public float         TruePeakBefore     { get; set; }
    public float         DrBefore           { get; set; }
    public float         LraBefore          { get; set; }
    public string        AnalysisJson       { get; set; } = "";
    public List<string>  ProblemTags        { get; set; } = new();

    // BPM / key / genre
    public float         Bpm                { get; set; }
    public string        Key                { get; set; } = "";
    public string        Genre              { get; set; } = "unknown";

    // Plan
    public MasteringPlan Plan               { get; set; } = new();

    // Results
    public string        OutputWav          { get; set; } = "";
    public string        ReportJson         { get; set; } = "";

    // Analysis — after
    public float         LufsAfter          { get; set; }
    public float         TruePeakAfter      { get; set; }
    public float         DrAfter            { get; set; }
    public float         LraAfter           { get; set; }
    public string        AnalysisAfterJson  { get; set; } = "";

    // State
    public string        JobId              { get; set; } = "";
    public string        LastResult         { get; set; } = "";
    public List<string>  Errors             { get; set; } = new();
}
