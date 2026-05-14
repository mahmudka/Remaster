using AudioPipeline.Shared.Models;
using Microsoft.EntityFrameworkCore;

namespace AudioPipeline.Shared.Data;

public class AudioPipelineContext : DbContext
{
    public AudioPipelineContext(DbContextOptions<AudioPipelineContext> options)
        : base(options) { }

    public DbSet<KnowledgeBook> KnowledgeBooks => Set<KnowledgeBook>();
    public DbSet<BookChunk> BookChunks => Set<BookChunk>();
    public DbSet<KnowledgeRule> KnowledgeBase => Set<KnowledgeRule>();
    public DbSet<MixSession> MixSessions => Set<MixSession>();
    public DbSet<TrackDiagnosis> TrackDiagnoses => Set<TrackDiagnosis>();
    public DbSet<ProcessingIteration> ProcessingIterations => Set<ProcessingIteration>();
    public DbSet<SimilarityReport> SimilarityReports => Set<SimilarityReport>();
    public DbSet<UserFeedback> UserFeedbacks => Set<UserFeedback>();
    public DbSet<LearnedRule> LearnedRules => Set<LearnedRule>();
    public DbSet<SkillProfile> SkillProfiles => Set<SkillProfile>();
    public DbSet<VoiceModel> VoiceModels => Set<VoiceModel>();

    // Keyless entity for stored procedure result
    public DbSet<BestParameterResult> BestParameterResults => Set<BestParameterResult>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        modelBuilder.Entity<KnowledgeBook>(e =>
        {
            e.HasMany(b => b.Chunks)
             .WithOne(c => c.Book)
             .HasForeignKey(c => c.BookId)
             .OnDelete(DeleteBehavior.Cascade);

            e.HasMany(b => b.Rules)
             .WithOne(r => r.Book)
             .HasForeignKey(r => r.BookId)
             .OnDelete(DeleteBehavior.Cascade);
        });

        modelBuilder.Entity<MixSession>(e =>
        {
            e.HasOne(s => s.Diagnosis)
             .WithOne(d => d.Session)
             .HasForeignKey<TrackDiagnosis>(d => d.SessionId)
             .OnDelete(DeleteBehavior.Cascade);

            e.HasMany(s => s.Iterations)
             .WithOne(i => i.Session)
             .HasForeignKey(i => i.SessionId)
             .OnDelete(DeleteBehavior.Cascade);

            e.HasMany(s => s.SimilarityReports)
             .WithOne(r => r.Session)
             .HasForeignKey(r => r.SessionId)
             .OnDelete(DeleteBehavior.Cascade);

            e.HasMany(s => s.Feedbacks)
             .WithOne(f => f.Session)
             .HasForeignKey(f => f.SessionId)
             .OnDelete(DeleteBehavior.Cascade);
        });

        modelBuilder.Entity<SimilarityReport>(e =>
        {
            e.HasOne(r => r.Iteration)
             .WithOne()
             .HasForeignKey<SimilarityReport>(r => r.IterationId)
             .OnDelete(DeleteBehavior.NoAction);
        });

        modelBuilder.Entity<BestParameterResult>().HasNoKey();

        // Indexes
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

    // Call stored procedure GetBestParameters
    public IQueryable<BestParameterResult> GetBestParameters(string genre)
        => BestParameterResults.FromSqlRaw("EXEC GetBestParameters @Genre = {0}", genre);

    // Call stored procedure UpdateLearning
    public Task UpdateLearningAsync(int sessionId)
        => Database.ExecuteSqlRawAsync("EXEC UpdateLearning @SessionId = {0}", sessionId);

    // Call stored procedure RecalculateLearnedRules
    public Task RecalculateLearnedRulesAsync(string genre)
        => Database.ExecuteSqlRawAsync("EXEC RecalculateLearnedRules @Genre = {0}", genre);

    public const string DefaultConnectionString =
        "Server=localhost;Database=AudioPipeline;Trusted_Connection=True;TrustServerCertificate=True;";
}

public class BestParameterResult
{
    public string RuleType { get; set; } = string.Empty;
    public string Genre { get; set; } = string.Empty;
    public string Parameter { get; set; } = string.Empty;
    public string Value { get; set; } = string.Empty;
    public string? Unit { get; set; }
    public double? Confidence { get; set; }
    public int? SampleCount { get; set; }
    public string? Rationale { get; set; }
    public string? Source { get; set; }
}
