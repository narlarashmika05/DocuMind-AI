import { describe, expect, it } from 'vitest'
import { isInProgress, stageLabel } from '../documents'
import { formatBytes } from '../format'
import { passwordProblem } from '../validation'
import { summarize, verdictInfo } from '../verification'

describe('passwordProblem', () => {
  it('mirrors the backend password rule', () => {
    expect(passwordProblem('short1')).toMatch(/at least 8/)
    expect(passwordProblem('onlyletters')).toMatch(/letter and one number/)
    expect(passwordProblem('Str0ngPass')).toBe('')
  })
})

describe('formatBytes', () => {
  it('uses readable units', () => {
    expect(formatBytes(512)).toBe('512 B')
    expect(formatBytes(2048)).toBe('2.0 KB')
    expect(formatBytes(5 * 1024 * 1024)).toBe('5.0 MB')
  })
})

describe('document status helpers', () => {
  it('knows which documents are still being processed', () => {
    expect(isInProgress({ status: 'uploaded' })).toBe(true)
    expect(isInProgress({ status: 'processing' })).toBe(true)
    expect(isInProgress({ status: 'ready' })).toBe(false)
  })

  it('describes the processing stage', () => {
    expect(stageLabel({ status: 'uploaded' })).toBe('Waiting to be processed')
    expect(stageLabel({ status: 'processing', processing_stage: 'embedding' })).toBe('Creating embeddings')
  })
})

describe('verification summary', () => {
  const claims = [{ verdict: 'supported' }, { verdict: 'unsupported' }, { verdict: 'contradicted' }, { verdict: 'not_checked' }]

  it('counts supported and flagged claims, ignoring unchecked ones', () => {
    expect(summarize(claims)).toEqual({ total: 4, checked: 3, supported: 1, flagged: 2 })
  })

  it('falls back to "not checked" for unknown verdicts', () => {
    expect(verdictInfo('something-new').label).toBe('Not checked')
  })
})
