namespace AudioPipeline.Shared.Models;

public class MasteringPlan
{
    public List<EqBand>    Eq             { get; set; } = new();
    public CompSettings?   Compression    { get; set; }
    public LimiterSettings Limiter        { get; set; } = new();
    public float           TargetLufs     { get; set; } = -14f;
    public float?          StereoWidth    { get; set; }
    public bool            DeNoise        { get; set; }
    public bool            DeClip         { get; set; }
    public bool            TransientShape { get; set; }
    public bool            DeEss          { get; set; }
    public float?          MonoBelowHz    { get; set; }
    public float?          HfGain         { get; set; }
    public List<string>    Sources        { get; set; } = new();
    public List<string>    AppliedTags    { get; set; } = new();
}

public class EqBand
{
    public float  Frequency { get; set; }
    public float  Gain      { get; set; }
    public float  Q         { get; set; } = 1f;
    public string Type      { get; set; } = "peak";
    // peak | notch | shelf_low | shelf_high | hp | lp
}

public class CompSettings
{
    public float Threshold  { get; set; } = -20f;
    public float Ratio      { get; set; } = 2f;
    public float Attack     { get; set; } = 10f;
    public float Release    { get; set; } = 100f;
    public bool  Expand     { get; set; } = false;
}

public class LimiterSettings
{
    public float Ceiling    { get; set; } = -1f;
    public float Release    { get; set; } = 50f;
}
