-- AudioPipeline — Database Setup
-- Block 1: Create database, tables, indexes, stored procedures, seed data

-- =============================================================================
-- DATABASE
-- =============================================================================

IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'AudioPipeline')
BEGIN
    CREATE DATABASE AudioPipeline;
    PRINT 'Database AudioPipeline created.';
END
ELSE
BEGIN
    PRINT 'Database AudioPipeline already exists.';
END
GO

USE AudioPipeline;
GO

-- =============================================================================
-- TABLES
-- =============================================================================

-- PDF books loaded into the system
IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'KnowledgeBooks')
BEGIN
    CREATE TABLE KnowledgeBooks (
        Id          INT           IDENTITY(1,1) PRIMARY KEY,
        Title       NVARCHAR(500) NOT NULL,
        Author      NVARCHAR(255),
        FilePath    NVARCHAR(1000),
        Genre       NVARCHAR(100) NULL,   -- NULL = applies to all genres
        Priority    INT           NOT NULL DEFAULT 1,  -- 1=base, 2=genre, 3=modern
        IsProcessed BIT           NOT NULL DEFAULT 0,
        TotalChunks INT           NOT NULL DEFAULT 0,
        CreatedAt   DATETIME2     NOT NULL DEFAULT GETDATE()
    );
    PRINT 'Table KnowledgeBooks created.';
END
GO

-- Text chunks extracted from books for RAG retrieval
IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'BookChunks')
BEGIN
    CREATE TABLE BookChunks (
        Id         INT           IDENTITY(1,1) PRIMARY KEY,
        BookId     INT           NOT NULL REFERENCES KnowledgeBooks(Id) ON DELETE CASCADE,
        ChunkIndex INT           NOT NULL,
        Content    NVARCHAR(MAX) NOT NULL,
        TokenCount INT,
        CreatedAt  DATETIME2     NOT NULL DEFAULT GETDATE()
    );
    PRINT 'Table BookChunks created.';
END
GO

-- Structured rules extracted from books (parameter/value pairs)
IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'KnowledgeBase')
BEGIN
    CREATE TABLE KnowledgeBase (
        Id        INT           IDENTITY(1,1) PRIMARY KEY,
        BookId    INT           NOT NULL REFERENCES KnowledgeBooks(Id) ON DELETE CASCADE,
        ChunkId   INT           NULL REFERENCES BookChunks(Id),
        Parameter NVARCHAR(200) NOT NULL,
        Value     NVARCHAR(500) NOT NULL,
        Unit      NVARCHAR(50),
        Genre     NVARCHAR(100) NULL,   -- NULL = applies to all genres
        Rationale NVARCHAR(MAX),
        Source    NVARCHAR(500),        -- e.g. "Bob Katz Ch.5", "Senior p.142"
        Priority  INT           NOT NULL DEFAULT 1,
        CreatedAt DATETIME2     NOT NULL DEFAULT GETDATE()
    );
    PRINT 'Table KnowledgeBase created.';
END
GO

-- Each audio file processing job
IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'MixSessions')
BEGIN
    CREATE TABLE MixSessions (
        Id          INT            IDENTITY(1,1) PRIMARY KEY,
        JobId       NVARCHAR(100)  NOT NULL,
        InputFile   NVARCHAR(1000) NOT NULL,
        OutputPath  NVARCHAR(1000),
        Genre       NVARCHAR(100),
        Bpm         FLOAT,
        [Key]       NVARCHAR(50),
        MixPlanJson NVARCHAR(MAX),
        Status      NVARCHAR(50)   NOT NULL DEFAULT 'Pending',  -- Pending/Running/Done/Failed
        BlocksRun   NVARCHAR(500),
        CreatedAt   DATETIME2      NOT NULL DEFAULT GETDATE(),
        CompletedAt DATETIME2      NULL
    );
    PRINT 'Table MixSessions created.';
END
GO

-- Frequency, dynamics and stereo analysis for a session
IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'TrackDiagnosis')
BEGIN
    CREATE TABLE TrackDiagnosis (
        Id                  INT       IDENTITY(1,1) PRIMARY KEY,
        SessionId           INT       NOT NULL REFERENCES MixSessions(Id) ON DELETE CASCADE,
        FrequencyMapJson    NVARCHAR(MAX),
        DynamicsProfileJson NVARCHAR(MAX),
        StereoProfileJson   NVARCHAR(MAX),
        ProblemsJson        NVARCHAR(MAX),
        CreatedAt           DATETIME2 NOT NULL DEFAULT GETDATE()
    );
    PRINT 'Table TrackDiagnosis created.';
END
GO

-- Each mix or master iteration within a session (max 3 each)
IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'ProcessingIterations')
BEGIN
    CREATE TABLE ProcessingIterations (
        Id              INT            IDENTITY(1,1) PRIMARY KEY,
        SessionId       INT            NOT NULL REFERENCES MixSessions(Id) ON DELETE CASCADE,
        IterationType   NVARCHAR(50)   NOT NULL,  -- 'mix' | 'master'
        IterationNumber INT            NOT NULL,
        ParametersJson  NVARCHAR(MAX),
        OutputFile      NVARCHAR(1000),
        LufsIntegrated  FLOAT          NULL,
        LufsTruePeak    FLOAT          NULL,
        CreatedAt       DATETIME2      NOT NULL DEFAULT GETDATE()
    );
    PRINT 'Table ProcessingIterations created.';
END
GO

-- Similarity score vs reference after each iteration
IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'SimilarityReports')
BEGIN
    CREATE TABLE SimilarityReports (
        Id               INT       IDENTITY(1,1) PRIMARY KEY,
        SessionId        INT       NOT NULL REFERENCES MixSessions(Id) ON DELETE CASCADE,
        IterationId      INT       NULL REFERENCES ProcessingIterations(Id),
        SimilarityScore  FLOAT,
        FrequencyDiffJson NVARCHAR(MAX),
        DynamicsDiffJson  NVARCHAR(MAX),
        ReportJson        NVARCHAR(MAX),
        CreatedAt         DATETIME2 NOT NULL DEFAULT GETDATE()
    );
    PRINT 'Table SimilarityReports created.';
END
GO

-- Star rating and problem tags from the user
IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'UserFeedback')
BEGIN
    CREATE TABLE UserFeedback (
        Id              INT           IDENTITY(1,1) PRIMARY KEY,
        SessionId       INT           NOT NULL REFERENCES MixSessions(Id) ON DELETE CASCADE,
        Rating          INT           NOT NULL CHECK (Rating BETWEEN 1 AND 5),
        FeedbackTagsJson NVARCHAR(500),  -- JSON array: ["bass_too_loud", "vocal_quiet"]
        UserNote        NVARCHAR(MAX),
        CreatedAt       DATETIME2     NOT NULL DEFAULT GETDATE()
    );
    PRINT 'Table UserFeedback created.';
END
GO

-- Rules derived from user feedback patterns (override KnowledgeBase)
IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'LearnedRules')
BEGIN
    CREATE TABLE LearnedRules (
        Id          INT           IDENTITY(1,1) PRIMARY KEY,
        Genre       NVARCHAR(100) NOT NULL,
        Parameter   NVARCHAR(200) NOT NULL,
        Value       NVARCHAR(500) NOT NULL,
        Unit        NVARCHAR(50),
        Confidence  FLOAT         NOT NULL DEFAULT 0.5,   -- 0.0 - 1.0
        SampleCount INT           NOT NULL DEFAULT 0,
        UpdatedAt   DATETIME2     NOT NULL DEFAULT GETDATE(),
        CreatedAt   DATETIME2     NOT NULL DEFAULT GETDATE()
    );
    PRINT 'Table LearnedRules created.';
END
GO

-- Genre-level skill profile generated after 20+ rated sessions
IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'SkillProfiles')
BEGIN
    CREATE TABLE SkillProfiles (
        Id             INT           IDENTITY(1,1) PRIMARY KEY,
        Genre          NVARCHAR(100) NOT NULL,
        ProfileName    NVARCHAR(200),
        ParametersJson NVARCHAR(MAX),
        SessionCount   INT           NOT NULL DEFAULT 0,
        AvgRating      FLOAT,
        CreatedAt      DATETIME2     NOT NULL DEFAULT GETDATE(),
        UpdatedAt      DATETIME2     NOT NULL DEFAULT GETDATE()
    );
    PRINT 'Table SkillProfiles created.';
END
GO

-- RVC voice models (Module 11, optional)
IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'VoiceModels')
BEGIN
    CREATE TABLE VoiceModels (
        Id          INT            IDENTITY(1,1) PRIMARY KEY,
        Name        NVARCHAR(200)  NOT NULL,
        ModelPath   NVARCHAR(1000) NOT NULL,
        IndexPath   NVARCHAR(1000),
        Description NVARCHAR(MAX),
        IsDefault   BIT            NOT NULL DEFAULT 0,
        CreatedAt   DATETIME2      NOT NULL DEFAULT GETDATE()
    );
    PRINT 'Table VoiceModels created.';
END
GO

-- =============================================================================
-- INDEXES
-- =============================================================================

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_BookChunks_BookId')
    CREATE INDEX IX_BookChunks_BookId ON BookChunks(BookId);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_KnowledgeBase_BookId')
    CREATE INDEX IX_KnowledgeBase_BookId ON KnowledgeBase(BookId);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_KnowledgeBase_Genre')
    CREATE INDEX IX_KnowledgeBase_Genre ON KnowledgeBase(Genre);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_KnowledgeBase_Parameter')
    CREATE INDEX IX_KnowledgeBase_Parameter ON KnowledgeBase(Parameter);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_MixSessions_JobId')
    CREATE INDEX IX_MixSessions_JobId ON MixSessions(JobId);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_MixSessions_Genre')
    CREATE INDEX IX_MixSessions_Genre ON MixSessions(Genre);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_TrackDiagnosis_SessionId')
    CREATE INDEX IX_TrackDiagnosis_SessionId ON TrackDiagnosis(SessionId);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_ProcessingIterations_SessionId')
    CREATE INDEX IX_ProcessingIterations_SessionId ON ProcessingIterations(SessionId);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_SimilarityReports_SessionId')
    CREATE INDEX IX_SimilarityReports_SessionId ON SimilarityReports(SessionId);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_UserFeedback_SessionId')
    CREATE INDEX IX_UserFeedback_SessionId ON UserFeedback(SessionId);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_LearnedRules_Genre')
    CREATE INDEX IX_LearnedRules_Genre ON LearnedRules(Genre);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_LearnedRules_Genre_Parameter')
    CREATE INDEX IX_LearnedRules_Genre_Parameter ON LearnedRules(Genre, Parameter);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_SkillProfiles_Genre')
    CREATE INDEX IX_SkillProfiles_Genre ON SkillProfiles(Genre);

GO
PRINT 'Indexes created.';
GO

-- =============================================================================
-- STORED PROCEDURES
-- =============================================================================

-- GetBestParameters: returns best parameters for a genre before each mix.
-- Priority order: LearnedRules (with 3+ samples) > KnowledgeBase by priority desc.
IF OBJECT_ID('dbo.GetBestParameters', 'P') IS NOT NULL
    DROP PROCEDURE dbo.GetBestParameters;
GO

CREATE PROCEDURE GetBestParameters
    @Genre NVARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        'learned'        AS RuleType,
        lr.Genre,
        lr.Parameter,
        lr.Value,
        lr.Unit,
        lr.Confidence,
        lr.SampleCount,
        NULL             AS Rationale,
        NULL             AS Source,
        0                AS SortPriority
    FROM LearnedRules lr
    WHERE lr.Genre = @Genre
      AND lr.SampleCount >= 3

    UNION ALL

    SELECT
        'knowledge'                          AS RuleType,
        ISNULL(kb.Genre, 'all')              AS Genre,
        kb.Parameter,
        kb.Value,
        kb.Unit,
        NULL                                 AS Confidence,
        NULL                                 AS SampleCount,
        kb.Rationale,
        kb.Source,
        b.Priority                           AS SortPriority
    FROM KnowledgeBase kb
    INNER JOIN KnowledgeBooks b ON kb.BookId = b.Id
    WHERE kb.Genre = @Genre OR kb.Genre IS NULL

    ORDER BY
        SortPriority DESC,
        RuleType ASC;
END
GO
PRINT 'Procedure GetBestParameters created.';
GO

-- UpdateLearning: called after user submits a rating.
-- Triggers RecalculateLearnedRules once 5+ high-rated sessions exist for the genre.
IF OBJECT_ID('dbo.UpdateLearning', 'P') IS NOT NULL
    DROP PROCEDURE dbo.UpdateLearning;
GO

CREATE PROCEDURE UpdateLearning
    @SessionId INT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @Genre       NVARCHAR(100);
    DECLARE @Rating      INT;

    SELECT
        @Genre  = ms.Genre,
        @Rating = uf.Rating
    FROM MixSessions ms
    INNER JOIN UserFeedback uf ON uf.SessionId = ms.Id
    WHERE ms.Id = @SessionId;

    IF @Rating IS NULL OR @Genre IS NULL
        RETURN;

    -- Only learn from ratings >= 4
    IF @Rating >= 4
    BEGIN
        DECLARE @HighRatedCount INT;
        SELECT @HighRatedCount = COUNT(*)
        FROM UserFeedback uf2
        INNER JOIN MixSessions ms2 ON ms2.Id = uf2.SessionId
        WHERE ms2.Genre = @Genre
          AND uf2.Rating >= 4;

        IF @HighRatedCount >= 5
            EXEC RecalculateLearnedRules @Genre;
    END
END
GO
PRINT 'Procedure UpdateLearning created.';
GO

-- RecalculateLearnedRules: rebuilds LearnedRules for a genre from high-rated sessions.
-- Called when 5+ sessions rated 4+ exist for the genre.
IF OBJECT_ID('dbo.RecalculateLearnedRules', 'P') IS NOT NULL
    DROP PROCEDURE dbo.RecalculateLearnedRules;
GO

CREATE PROCEDURE RecalculateLearnedRules
    @Genre NVARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @AvgRating   FLOAT;
    DECLARE @SampleCount INT;

    SELECT
        @AvgRating   = AVG(CAST(uf.Rating AS FLOAT)),
        @SampleCount = COUNT(*)
    FROM UserFeedback uf
    INNER JOIN MixSessions ms ON ms.Id = uf.SessionId
    WHERE ms.Genre = @Genre
      AND uf.Rating >= 4;

    -- Update or insert SkillProfile for this genre
    IF EXISTS (SELECT 1 FROM SkillProfiles WHERE Genre = @Genre)
    BEGIN
        UPDATE SkillProfiles
        SET SessionCount = @SampleCount,
            AvgRating    = @AvgRating,
            UpdatedAt    = GETDATE()
        WHERE Genre = @Genre;
    END
    ELSE
    BEGIN
        INSERT INTO SkillProfiles (Genre, ProfileName, SessionCount, AvgRating)
        VALUES (@Genre, @Genre + N' Profile', @SampleCount, @AvgRating);
    END

    -- Placeholder: real parameter aggregation is done by the Python learning_engine
    -- which parses ProcessingIterations.ParametersJson and writes back to LearnedRules.
    PRINT 'RecalculateLearnedRules completed for genre: ' + @Genre;
END
GO
PRINT 'Procedure RecalculateLearnedRules created.';
GO

-- =============================================================================
-- SEED DATA — 9 books from SKILL.md
-- =============================================================================

IF NOT EXISTS (SELECT 1 FROM KnowledgeBooks)
BEGIN
    INSERT INTO KnowledgeBooks (Title, Author, Genre, Priority, IsProcessed)
    VALUES
    -- Base books (Priority 1 — all genres)
    (N'Mixing Secrets for the Small Studio',          N'Mike Senior',      NULL,      1, 0),
    (N'The Art of Mixing',                            N'David Gibson',     NULL,      1, 0),
    (N'The Mixing Engineer''s Handbook',              N'Bobby Owsinski',   NULL,      1, 0),
    (N'Mastering Audio',                              N'Bob Katz',         NULL,      1, 0),
    (N'The Mastering Engineer''s Handbook',           N'Bobby Owsinski',   NULL,      1, 0),
    -- Genre-specific books (Priority 2)
    (N'Dance Music Manual',                           N'Rick Snoman',      N'edm',    2, 0),
    (N'The Music Producer''s Handbook',               N'Bobby Owsinski',   N'hip-hop',2, 0),
    (N'Recording and Producing in the Home Studio',   N'David Franz',      N'live',   2, 0),
    (N'Mixing Vocals',                                N'Various',          N'vocal',  2, 0);

    PRINT '9 seed books inserted into KnowledgeBooks.';
END
ELSE
BEGIN
    PRINT 'KnowledgeBooks already contains data — seed skipped.';
END
GO

PRINT '';
PRINT '=== AudioPipeline database setup complete ===';
GO
