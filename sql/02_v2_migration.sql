USE AudioPipeline;
GO

-- Drop FK from KnowledgeBase -> BookChunks before dropping BookChunks
DECLARE @sql NVARCHAR(500);
SELECT @sql = 'ALTER TABLE KnowledgeBase DROP CONSTRAINT ' + QUOTENAME(fk.name)
FROM sys.foreign_keys fk
JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
JOIN sys.columns c ON fkc.parent_object_id = c.object_id AND fkc.parent_column_id = c.column_id
WHERE OBJECT_NAME(fk.parent_object_id) = 'KnowledgeBase'
  AND c.name = 'ChunkId';
IF @sql IS NOT NULL EXEC(@sql);
GO

-- Drop obsolete tables
IF OBJECT_ID('SimilarityReports','U')    IS NOT NULL DROP TABLE SimilarityReports;
IF OBJECT_ID('ProcessingIterations','U') IS NOT NULL DROP TABLE ProcessingIterations;
IF OBJECT_ID('TrackDiagnosis','U')       IS NOT NULL DROP TABLE TrackDiagnosis;
IF OBJECT_ID('BookChunks','U')           IS NOT NULL DROP TABLE BookChunks;
IF OBJECT_ID('VoiceModels','U')          IS NOT NULL DROP TABLE VoiceModels;
GO

-- Drop ChunkId column from KnowledgeBase (no longer needed)
IF COL_LENGTH('KnowledgeBase','ChunkId') IS NOT NULL
    ALTER TABLE KnowledgeBase DROP COLUMN ChunkId;
GO

-- Add new columns to MixSessions
IF COL_LENGTH('MixSessions','AnalysisBeforeJson') IS NULL
    ALTER TABLE MixSessions ADD AnalysisBeforeJson NVARCHAR(MAX) NULL;
IF COL_LENGTH('MixSessions','AnalysisAfterJson') IS NULL
    ALTER TABLE MixSessions ADD AnalysisAfterJson NVARCHAR(MAX) NULL;
IF COL_LENGTH('MixSessions','PlanJson') IS NULL
    ALTER TABLE MixSessions ADD PlanJson NVARCHAR(MAX) NULL;
IF COL_LENGTH('MixSessions','ProblemsDetected') IS NULL
    ALTER TABLE MixSessions ADD ProblemsDetected NVARCHAR(1000) NULL;
GO

-- Drop obsolete columns from MixSessions
IF COL_LENGTH('MixSessions','MixPlanJson') IS NOT NULL
    ALTER TABLE MixSessions DROP COLUMN MixPlanJson;
IF COL_LENGTH('MixSessions','BlocksRun') IS NOT NULL
    ALTER TABLE MixSessions DROP COLUMN BlocksRun;
IF COL_LENGTH('MixSessions','RvcModelPath') IS NOT NULL
    ALTER TABLE MixSessions DROP COLUMN RvcModelPath;
GO

-- Add Tags column to KnowledgeBase
IF COL_LENGTH('KnowledgeBase','Tags') IS NULL
    ALTER TABLE KnowledgeBase ADD Tags NVARCHAR(500) NULL;
GO

-- Tag existing rules
UPDATE KnowledgeBase SET Tags = '["muddy_lowmid"]'
  WHERE Tags IS NULL
    AND (Parameter LIKE '%low%mid%' OR Parameter LIKE '%mud%'
         OR Rationale LIKE '%200 Hz%' OR Rationale LIKE '%300 Hz%'
         OR Rationale LIKE '%400 Hz%');

UPDATE KnowledgeBase SET Tags = '["over_compressed","missing_transients"]'
  WHERE Tags IS NULL
    AND (Parameter LIKE '%compres%' OR Parameter LIKE '%dynamic%'
         OR Parameter LIKE '%transient%' OR Parameter LIKE '%punch%');

UPDATE KnowledgeBase SET Tags = '["loudness_mismatch"]'
  WHERE Tags IS NULL
    AND (Parameter LIKE '%lufs%' OR Parameter LIKE '%loudness%'
         OR Parameter LIKE '%level%' OR Parameter LIKE '%gain%');

UPDATE KnowledgeBase SET Tags = '["metallic_resonance","harsh_highmid"]'
  WHERE Tags IS NULL
    AND (Parameter LIKE '%eq%' OR Parameter LIKE '%resonan%'
         OR Parameter LIKE '%harsh%' OR Rationale LIKE '%kHz%');

UPDATE KnowledgeBase SET Tags = '["ai_noise"]'
  WHERE Tags IS NULL
    AND (Parameter LIKE '%noise%' OR Parameter LIKE '%floor%'
         OR Parameter LIKE '%hiss%');

UPDATE KnowledgeBase SET Tags = '["sibilance"]'
  WHERE Tags IS NULL
    AND (Parameter LIKE '%sibilanc%' OR Parameter LIKE '%de-ess%');

UPDATE KnowledgeBase SET Tags = '["sub_issues"]'
  WHERE Tags IS NULL
    AND (Parameter LIKE '%sub%bass%' OR Rationale LIKE '%60 Hz%');

UPDATE KnowledgeBase SET Tags = '["spectral_smearing"]'
  WHERE Tags IS NULL
    AND (Parameter LIKE '%high%freq%' OR Parameter LIKE '%air%'
         OR Rationale LIKE '%16 kHz%');

UPDATE KnowledgeBase SET Tags = '["general"]' WHERE Tags IS NULL;
GO

-- Verify
SELECT 'present' AS Status, TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_NAME IN ('KnowledgeBooks','KnowledgeBase','MixSessions',
                     'UserFeedback','LearnedRules','SkillProfiles')
ORDER BY TABLE_NAME;

SELECT 'should_be_gone' AS Status, TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_NAME IN ('BookChunks','SimilarityReports','ProcessingIterations',
                     'TrackDiagnosis','VoiceModels');

SELECT Tags, COUNT(*) AS RuleCount
FROM KnowledgeBase
GROUP BY Tags
ORDER BY RuleCount DESC;

PRINT 'Migration v2 complete';
GO
