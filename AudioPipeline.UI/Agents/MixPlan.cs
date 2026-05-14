namespace AudioPipeline.UI.Agents;

public class MixPlan
{
    public List<TrackRecommendation> Tracks  { get; set; } = new();
    public BusRecommendation?        Bus     { get; set; }
    public ReverbSettings?           Reverb  { get; set; }
    public DelaySettings?            Delay   { get; set; }
    public List<string>              Sources { get; set; } = new();
}

public class TrackRecommendation
{
    public string        Track      { get; set; } = "";
    public List<EqBand>  Eq         { get; set; } = new();
    public CompSettings? Comp       { get; set; }
    public float         Gain       { get; set; } = 0;
    public float         Pan        { get; set; } = 0;
    public string        Rationale  { get; set; } = "";
    public string        BookSource { get; set; } = "";
}

public class EqBand
{
    public float  Frequency { get; set; }
    public float  Gain      { get; set; }
    public float  Q         { get; set; } = 1.0f;
    public string Type      { get; set; } = "peak";
}

public class CompSettings
{
    public float Threshold  { get; set; } = -20;
    public float Ratio      { get; set; } = 4;
    public float Attack     { get; set; } = 10;
    public float Release    { get; set; } = 100;
    public float MakeupGain { get; set; } = 0;
}

public class BusRecommendation
{
    public CompSettings? Compression { get; set; }
    public List<EqBand>  Eq          { get; set; } = new();
}

public class ReverbSettings
{
    public float RoomSize { get; set; } = 0.5f;
    public float Damping  { get; set; } = 0.5f;
    public float WetLevel { get; set; } = 0.15f;
    public float DryLevel { get; set; } = 0.85f;
    public float PreDelay { get; set; } = 20;
}

public class DelaySettings
{
    public float Time     { get; set; } = 250;
    public float Feedback { get; set; } = 0.3f;
    public float WetLevel { get; set; } = 0.2f;
}
