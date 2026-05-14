namespace AudioPipeline.UI.Agents;

public enum PipelineBlock
{
    Analysis  = 1,
    Stems     = 2,
    Midi      = 3,
    Vst       = 4,
    Rvc       = 5,
    Knowledge = 6,
    Mix       = 7,
    Master    = 8,
}

public class PipelineContext
{
    // Input
    public string  JobId         { get; set; } = "";
    public string  InputFile     { get; set; } = "";
    public string  OutputPath    { get; set; } = "";
    public string? ReferenceFile { get; set; }
    public string? RvcModelPath  { get; set; }
    public string? RvcIndexPath  { get; set; }

    // Analysis
    public float  Bpm              { get; set; }
    public string Key              { get; set; } = "";
    public string Genre            { get; set; } = "unknown";
    public string? FrequencyMap    { get; set; }
    public string? DynamicsProfile { get; set; }
    public string? StereoProfile   { get; set; }

    // Stems
    public string? VocalStem       { get; set; }
    public string? BassStem        { get; set; }
    public string? DrumsStem       { get; set; }
    public string? InstrumentsStem { get; set; }

    // MIDI
    public string? BassMidi        { get; set; }
    public string? DrumsMidi       { get; set; }
    public string? InstrumentsMidi { get; set; }

    // VST render
    public string? BassVst         { get; set; }
    public string? DrumsVst        { get; set; }
    public string? InstrumentsVst  { get; set; }

    // RVC vocal
    public string? VocalRvc        { get; set; }

    // Mix plan from KnowledgeAgent
    public MixPlan? MixPlan        { get; set; }

    // Results
    public string? MixFile         { get; set; }
    public string? MasterWav       { get; set; }
    public string? MasterMp3       { get; set; }
    public string? ReportJson      { get; set; }

    // State
    public string       LastResult { get; set; } = "";
    public List<string> Errors     { get; set; } = new();
    public List<string> BlocksRun  { get; set; } = new();
}
