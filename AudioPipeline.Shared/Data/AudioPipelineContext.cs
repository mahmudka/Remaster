using AudioPipeline.Shared.Models;
using Microsoft.EntityFrameworkCore;

namespace AudioPipeline.Shared.Data;

public class AudioPipelineContext : DbContext
{
    public AudioPipelineContext(DbContextOptions<AudioPipelineContext> options)
        : base(options) { }

    public DbSet<KnowledgeBook>  KnowledgeBooks  => Set<KnowledgeBook>();
    public DbSet<KnowledgeRule>  KnowledgeBase   => Set<KnowledgeRule>();
    public DbSet<MixSession>     MixSessions     => Set<MixSession>();
    public DbSet<UserFeedback>   UserFeedbacks   => Set<UserFeedback>();
    public DbSet<LearnedRule>    LearnedRules    => Set<LearnedRule>();
    public DbSet<SkillProfile>   SkillProfiles   => Set<SkillProfile>();

    public DbSet<BestParameterResult> BestParameterResults => Set<BestParameterResult>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        modelBuilder.Entity<KnowledgeBook>(e =>
        {
            e.HasMany(b => b.Rules)
             .WithOne(r => r.Book)
             .HasForeignKey(r => r.BookId)
             .OnDelete(DeleteBehavior.Cascade);
        });

        modelBuilder.Entity<MixSession>(e =>
        {
            e.HasMany(s => s.Feedbacks)
             .WithOne(f => f.Session)
             .HasForeignKey(f => f.SessionId)
             .OnDelete(DeleteBehavior.Cascade);
        });

        modelBuilder.Entity<BestParameterResult>().HasNoKey();

        modelBuilder.Entity<KnowledgeRule>()
            .HasIndex(r => r.Genre);
        modelBuilder.Entity<KnowledgeRule>()
            .HasIndex(r => r.Parameter);
        modelBuilder.Entity<MixSession>()
            .HasIndex(s => s.JobId);
        modelBuilder.Entity<MixSession>()
            .HasIndex(s => s.Genre);
        modelBuilder.Entity<LearnedRule>()
            .HasIndex(r => new { r.Genre, r.Parameter });
        modelBuilder.Entity<SkillProfile>()
            .HasIndex(p => p.Genre);
    }

    public IQueryable<BestParameterResult> GetBestParameters(string genre)
        => BestParameterResults.FromSqlRaw("EXEC GetBestParameters @Genre = {0}", genre);

    public Task UpdateLearningAsync(int sessionId)
        => Database.ExecuteSqlRawAsync("EXEC UpdateLearning @SessionId = {0}", sessionId);

    public Task RecalculateLearnedRulesAsync(string genre)
        => Database.ExecuteSqlRawAsync("EXEC RecalculateLearnedRules @Genre = {0}", genre);

    public const string DefaultConnectionString =
        "Server=localhost;Database=AudioPipeline;Trusted_Connection=True;TrustServerCertificate=True;";
}

public class BestParameterResult
{
    public string  RuleType    { get; set; } = string.Empty;
    public string  Genre       { get; set; } = string.Empty;
    public string  Parameter   { get; set; } = string.Empty;
    public string  Value       { get; set; } = string.Empty;
    public string? Unit        { get; set; }
    public double? Confidence  { get; set; }
    public int?    SampleCount { get; set; }
    public string? Rationale   { get; set; }
    public string? Source      { get; set; }
}
