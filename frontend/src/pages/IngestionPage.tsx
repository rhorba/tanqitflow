import { useState, useRef, DragEvent, ChangeEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../lib/api'

type JobType = 'dma_inflow' | 'customer_reads' | 'pressure_flow'
type JobStatus = 'queued' | 'processing' | 'done' | 'error'

interface Job {
  id: string
  job_type: JobType
  original_filename: string
  status: JobStatus
  row_count: number | null
  error_detail: string | null
  created_at: string
  completed_at: string | null
}

const STATUS_COLORS: Record<JobStatus, string> = {
  queued: 'bg-yellow-100 text-yellow-800',
  processing: 'bg-blue-100 text-blue-800',
  done: 'bg-green-100 text-green-800',
  error: 'bg-red-100 text-red-800',
}

export default function IngestionPage() {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [jobType, setJobType] = useState<JobType>('dma_inflow')
  const [dragOver, setDragOver] = useState(false)
  const [uploadError, setUploadError] = useState('')

  const { data: jobsData, isLoading } = useQuery({
    queryKey: ['ingestion-jobs'],
    queryFn: () => api.get<{ data: Job[]; meta: object }>('/ingestion/jobs').then(r => r.data),
    refetchInterval: 5000, // poll every 5s while jobs are active
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData()
      form.append('file', file)
      form.append('job_type', jobType)
      return api.post('/ingestion/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ingestion-jobs'] })
      setUploadError('')
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setUploadError(msg || t('common.error'))
    },
  })

  function handleFile(file: File) {
    setUploadError('')
    if (file.size > 50 * 1024 * 1024) {
      setUploadError(t('ingestion.file_too_large'))
      return
    }
    uploadMutation.mutate(file)
  }

  function onDrop(e: DragEvent) {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  function onFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
    e.target.value = ''
  }

  const jobs = jobsData?.data ?? []

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <h1 className="text-2xl font-bold text-gray-800">{t('ingestion.title')}</h1>

      {/* Job type selector */}
      <div className="flex flex-wrap gap-2">
        {(['dma_inflow', 'customer_reads', 'pressure_flow'] as JobType[]).map(jt => (
          <button
            key={jt}
            onClick={() => setJobType(jt)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              jobType === jt
                ? 'bg-teal-600 text-white'
                : 'bg-white border border-gray-300 text-gray-700 hover:border-teal-400'
            }`}
          >
            {t(`ingestion.type_${jt}`)}
          </button>
        ))}
      </div>

      {/* Dropzone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
          dragOver
            ? 'border-teal-500 bg-teal-50'
            : 'border-gray-300 bg-white hover:border-teal-400'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx"
          className="hidden"
          onChange={onFileChange}
        />
        <div className="text-4xl mb-3">📂</div>
        <p className="text-gray-700 font-medium">
          {uploadMutation.isPending ? t('common.loading') : t('ingestion.drop_here')}
        </p>
        <p className="text-sm text-gray-400 mt-1">{t('ingestion.file_types')}</p>
      </div>

      {uploadError && (
        <p role="alert" className="text-red-600 text-sm">{uploadError}</p>
      )}

      {/* Jobs table */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-700">{t('ingestion.history')}</h2>
        </div>
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">{t('common.loading')}</div>
        ) : jobs.length === 0 ? (
          <div className="p-8 text-center text-gray-400">{t('ingestion.no_jobs')}</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-start font-medium text-gray-600">{t('ingestion.filename')}</th>
                <th className="px-4 py-3 text-start font-medium text-gray-600">{t('ingestion.type')}</th>
                <th className="px-4 py-3 text-start font-medium text-gray-600">{t('ingestion.status')}</th>
                <th className="px-4 py-3 text-start font-medium text-gray-600">{t('ingestion.rows')}</th>
                <th className="px-4 py-3 text-start font-medium text-gray-600">{t('ingestion.date')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {jobs.map(job => (
                <tr key={job.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-800 truncate max-w-xs" title={job.original_filename}>
                    {job.original_filename}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {t(`ingestion.type_${job.job_type}`)}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[job.status]}`}>
                      {t(`ingestion.status_${job.status}`)}
                    </span>
                    {job.error_detail && (
                      <p className="text-red-500 text-xs mt-0.5 truncate max-w-xs" title={job.error_detail}>
                        {job.error_detail}
                      </p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {job.row_count != null ? job.row_count.toLocaleString() : '—'}
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {new Date(job.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
