export type Classification = 'LIKELY_AUTHENTIC' | 'LIKELY_MANIPULATED' | 'INCONCLUSIVE';
export type AnalysisStatus = 'CREATED' | 'VALIDATING' | 'DECODING' | 'QUALITY_CHECK' | 'EXTRACTING_FRAMES' | 'DETECTING_FACES' | 'PREPROCESSING' | 'MODEL_INFERENCE' | 'GENERATING_EVIDENCE' | 'AGGREGATING' | 'AI_EXPLANATION' | 'COMPLETED' | 'FAILED';

export interface User {id: string; name: string; email: string; created_at: string}
export interface Analysis {
  id: string; media_type: 'IMAGE'|'VIDEO'; original_filename: string; mime_type: string; file_size: number;
  sha256: string; width?: number; height?: number; duration?: number; fps?: number; status: AnalysisStatus;
  mode: string; model_id?: string; model_version?: string; fake_probability?: number; real_probability?: number;
  classification?: Classification; quality_status?: 'GOOD'|'LIMITED'|'POOR'; analysis_scope?: string;
  analysed_frames: number; valid_frames: number; aggregate?: Record<string, unknown>; thresholds?: Record<string, unknown>;
  failure_reason?: string; created_at: string; completed_at?: string; has_preview: boolean;
  review?: {decision: string; rationale?: string; created_at: string};
  quality?: {status: string; blur_score: number; brightness: number; contrast: number; face_detected: boolean; face_box?: Record<string, number>; warnings: string[]; details?: Record<string, string>};
  evidence?: {available: boolean; method: string; has_attention: boolean; has_heatmap: boolean; has_overlay: boolean; has_crop: boolean; metadata?: Record<string, unknown>};
  events?: {id: string; stage: string; message: string; metadata?: Record<string, unknown>; created_at: string}[];
  notes?: {id: string; note: string; created_at: string}[];
  explanation?: Explanation;
}
export interface Frame {id: string; frame_index: number; timestamp_ms: number; width: number; height: number; face_detected: boolean; quality_status: string; fake_probability?: number; real_probability?: number; classification?: Classification; attention_available: boolean}
export interface Explanation {summary: string; evidence_interpretation: string; quality_context: string; recommended_review: string; limitations: string; provider?: string}

