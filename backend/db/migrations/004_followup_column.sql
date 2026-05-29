-- Migration 004: Add follow_up_1_sent_at column to leads table
-- Pre-requisite for Story 4.2 (followup query service)
--
-- This column tracks when the first follow-up message was sent to a lead.
-- NULL means no first follow-up has been sent yet.
-- Used by the follow-up scheduler to determine eligibility for first and second follow-up attempts.

ALTER TABLE leads
    ADD COLUMN IF NOT EXISTS follow_up_1_sent_at TIMESTAMPTZ DEFAULT NULL;
