import { useState, useEffect } from 'react'
import { api } from '../lib/api'

interface SummaryData {
  overall_match_pct: number
  verdict: string
  must_have_coverage: {
    covered: string[]
    missing: string[]
    partially_covered: string[]
  }
  experience_breakdown: {
    total_years: number
    key_skills: Array<{ skill: string; years: number }>
  }
  salary_info: {
    expectation_min?: number
    expectation_max?: number
    vacancy_range_min?: number
    vacancy_range_max?: number
    currency: string
    match: string
  }
  location_format: {
    candidate_city: string
    vacancy_city: string
    employment_type: string
    relocation_ready: boolean
    match: boolean
  }
  availability: {
    ready_in_weeks?: number
    notes: string
  }
  language_proficiency: Record<string, string>
  portfolio_links: Array<{ type: string; url: string }>
  risks: Array<{ severity: string; risk: string }>
  summary: {
    one_liner: string
    strengths: string[]
    concerns: string[]
  }
  transcript_id?: string
}

export default function InterviewSummary({ responseId }: { responseId: string }) {
  const [summary, setSummary] = useState<SummaryData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        setLoading(true)
        const res = await api.get(`/responses/${responseId}/summary`)
        setSummary(res.data)
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load summary')
      } finally {
        setLoading(false)
      }
    }

    if (responseId) {
      fetchSummary()
    }
  }, [responseId])

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-3/4"></div>
          <div className="h-4 bg-gray-200 rounded w-full"></div>
          <div className="h-4 bg-gray-200 rounded w-5/6"></div>
        </div>
      </div>
    )
  }

  if (error || !summary) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-red-600">
          {error || 'Summary not available'}
        </div>
      </div>
    )
  }

  const getVerdictColor = (verdict: string) => {
    if (verdict === 'подходит') return 'bg-green-100 text-green-800 border-green-300'
    if (verdict === 'сомнительно') return 'bg-yellow-100 text-yellow-800 border-yellow-300'
    return 'bg-red-100 text-red-800 border-red-300'
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      {/* Header with Score */}
      <div className="bg-gradient-to-r from-blue-500 to-blue-600 p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">Итоговая оценка кандидата</h2>
            <p className="text-blue-100 mt-1">{summary.summary.one_liner}</p>
          </div>
          <div className="text-right">
            <div className="text-5xl font-bold">{summary.overall_match_pct}%</div>
            <div className={`mt-2 px-4 py-1 rounded-full border-2 ${getVerdictColor(summary.verdict)} inline-block`}>
              {summary.verdict === 'подходит' ? '✅ Подходит' :
               summary.verdict === 'сомнительно' ? '⚠️ Сомнительно' : '❌ Не подходит'}
            </div>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Must-Have Coverage */}
        <section>
          <h3 className="text-lg font-semibold mb-3 text-gray-900">📋 Покрытие обязательных навыков</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-green-50 p-4 rounded-lg">
              <div className="text-sm text-green-700 font-medium mb-2">Есть</div>
              <div className="flex flex-wrap gap-2">
                {summary.must_have_coverage.covered.length > 0 ? (
                  summary.must_have_coverage.covered.map((skill, i) => (
                    <span key={i} className="px-2 py-1 bg-green-200 text-green-800 rounded text-sm">
                      {skill}
                    </span>
                  ))
                ) : (
                  <span className="text-gray-500 text-sm">—</span>
                )}
              </div>
            </div>
            <div className="bg-yellow-50 p-4 rounded-lg">
              <div className="text-sm text-yellow-700 font-medium mb-2">Частично</div>
              <div className="flex flex-wrap gap-2">
                {summary.must_have_coverage.partially_covered.length > 0 ? (
                  summary.must_have_coverage.partially_covered.map((skill, i) => (
                    <span key={i} className="px-2 py-1 bg-yellow-200 text-yellow-800 rounded text-sm">
                      {skill}
                    </span>
                  ))
                ) : (
                  <span className="text-gray-500 text-sm">—</span>
                )}
              </div>
            </div>
            <div className="bg-red-50 p-4 rounded-lg">
              <div className="text-sm text-red-700 font-medium mb-2">Отсутствует</div>
              <div className="flex flex-wrap gap-2">
                {summary.must_have_coverage.missing.length > 0 ? (
                  summary.must_have_coverage.missing.map((skill, i) => (
                    <span key={i} className="px-2 py-1 bg-red-200 text-red-800 rounded text-sm">
                      {skill}
                    </span>
                  ))
                ) : (
                  <span className="text-gray-500 text-sm">—</span>
                )}
              </div>
            </div>
          </div>
        </section>

        {/* Experience Breakdown */}
        <section>
          <h3 className="text-lg font-semibold mb-3 text-gray-900">💼 Опыт работы</h3>
          <div className="bg-gray-50 p-4 rounded-lg">
            <div className="mb-3">
              <span className="text-gray-600">Общий опыт:</span>{' '}
              <span className="font-semibold text-gray-900">
                {summary.experience_breakdown.total_years} {summary.experience_breakdown.total_years === 1 ? 'год' : 'лет'}
              </span>
            </div>
            {summary.experience_breakdown.key_skills.length > 0 && (
              <div className="space-y-2">
                <div className="text-sm text-gray-600 font-medium">По ключевым навыкам:</div>
                {summary.experience_breakdown.key_skills.map((item, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <span className="text-gray-700">{item.skill}</span>
                    <span className="font-medium text-gray-900">{item.years} лет</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Salary & Location */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Salary */}
          <section>
            <h3 className="text-lg font-semibold mb-3 text-gray-900">💰 Зарплатные ожидания</h3>
            <div className="bg-gray-50 p-4 rounded-lg space-y-2">
              <div>
                <span className="text-gray-600 text-sm">Ожидания кандидата:</span>{' '}
                <div className="font-semibold text-gray-900">
                  {summary.salary_info.expectation_min && summary.salary_info.expectation_max ? (
                    `${summary.salary_info.expectation_min.toLocaleString()} - ${summary.salary_info.expectation_max.toLocaleString()} ${summary.salary_info.currency}`
                  ) : (
                    'Не указано'
                  )}
                </div>
              </div>
              <div>
                <span className="text-gray-600 text-sm">Вилка вакансии:</span>{' '}
                <div className="font-semibold text-gray-900">
                  {summary.salary_info.vacancy_range_min && summary.salary_info.vacancy_range_max ? (
                    `${summary.salary_info.vacancy_range_min.toLocaleString()} - ${summary.salary_info.vacancy_range_max.toLocaleString()} ${summary.salary_info.currency}`
                  ) : (
                    'Не указано'
                  )}
                </div>
              </div>
              <div className={`mt-2 px-3 py-1 rounded text-sm font-medium inline-block ${
                summary.salary_info.match === 'подходит' ? 'bg-green-100 text-green-800' :
                summary.salary_info.match === 'выше ожиданий' ? 'bg-yellow-100 text-yellow-800' :
                'bg-red-100 text-red-800'
              }`}>
                {summary.salary_info.match}
              </div>
            </div>
          </section>

          {/* Location */}
          <section>
            <h3 className="text-lg font-semibold mb-3 text-gray-900">📍 Локация и формат</h3>
            <div className="bg-gray-50 p-4 rounded-lg space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Город кандидата:</span>
                <span className="font-medium text-gray-900">{summary.location_format.candidate_city}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Город вакансии:</span>
                <span className="font-medium text-gray-900">{summary.location_format.vacancy_city}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Формат:</span>
                <span className="font-medium text-gray-900">{summary.location_format.employment_type}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Готов к переезду:</span>
                <span className={`font-medium ${summary.location_format.relocation_ready ? 'text-green-600' : 'text-red-600'}`}>
                  {summary.location_format.relocation_ready ? 'Да' : 'Нет'}
                </span>
              </div>
            </div>
          </section>
        </div>

        {/* Availability & Languages */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <section>
            <h3 className="text-lg font-semibold mb-3 text-gray-900">📅 Доступность</h3>
            <div className="bg-gray-50 p-4 rounded-lg">
              {summary.availability.ready_in_weeks ? (
                <div className="text-gray-900">
                  Может выйти через <span className="font-semibold">{summary.availability.ready_in_weeks} недель</span>
                </div>
              ) : (
                <div className="text-gray-500">Не указано</div>
              )}
              {summary.availability.notes && (
                <div className="text-sm text-gray-600 mt-2">{summary.availability.notes}</div>
              )}
            </div>
          </section>

          <section>
            <h3 className="text-lg font-semibold mb-3 text-gray-900">🌍 Языки</h3>
            <div className="bg-gray-50 p-4 rounded-lg space-y-2">
              {Object.keys(summary.language_proficiency).length > 0 ? (
                Object.entries(summary.language_proficiency).map(([lang, level]) => (
                  <div key={lang} className="flex items-center justify-between text-sm">
                    <span className="text-gray-700 capitalize">{lang}</span>
                    <span className="font-medium text-gray-900">{level}</span>
                  </div>
                ))
              ) : (
                <div className="text-gray-500 text-sm">Не указано</div>
              )}
            </div>
          </section>
        </div>

        {/* Portfolio Links */}
        {summary.portfolio_links.length > 0 && (
          <section>
            <h3 className="text-lg font-semibold mb-3 text-gray-900">🔗 Портфолио</h3>
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="flex flex-wrap gap-3">
                {summary.portfolio_links.map((link, i) => (
                  <a
                    key={i}
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition"
                  >
                    <span className="capitalize">{link.type}</span>
                    <span>↗</span>
                  </a>
                ))}
              </div>
            </div>
          </section>
        )}

        {/* Risks */}
        {summary.risks.length > 0 && (
          <section>
            <h3 className="text-lg font-semibold mb-3 text-gray-900">⚠️ Риски</h3>
            <div className="space-y-2">
              {summary.risks.map((risk, i) => (
                <div
                  key={i}
                  className={`p-3 rounded-lg border-l-4 ${
                    risk.severity === 'high' ? 'bg-red-50 border-red-500' :
                    risk.severity === 'medium' ? 'bg-yellow-50 border-yellow-500' :
                    'bg-blue-50 border-blue-500'
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <span className={`text-xs font-semibold uppercase ${
                      risk.severity === 'high' ? 'text-red-700' :
                      risk.severity === 'medium' ? 'text-yellow-700' :
                      'text-blue-700'
                    }`}>
                      {risk.severity}
                    </span>
                    <span className="text-gray-700 text-sm flex-1">{risk.risk}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Strengths & Concerns */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <section>
            <h3 className="text-lg font-semibold mb-3 text-green-700">✅ Сильные стороны</h3>
            <div className="bg-green-50 p-4 rounded-lg">
              {summary.summary.strengths.length > 0 ? (
                <ul className="space-y-1">
                  {summary.summary.strengths.map((strength, i) => (
                    <li key={i} className="text-sm text-gray-700">• {strength}</li>
                  ))}
                </ul>
              ) : (
                <div className="text-gray-500 text-sm">Не указано</div>
              )}
            </div>
          </section>

          <section>
            <h3 className="text-lg font-semibold mb-3 text-yellow-700">⚠️ Вопросы</h3>
            <div className="bg-yellow-50 p-4 rounded-lg">
              {summary.summary.concerns.length > 0 ? (
                <ul className="space-y-1">
                  {summary.summary.concerns.map((concern, i) => (
                    <li key={i} className="text-sm text-gray-700">• {concern}</li>
                  ))}
                </ul>
              ) : (
                <div className="text-gray-500 text-sm">Нет вопросов</div>
              )}
            </div>
          </section>
        </div>

        {/* Transcript Link */}
        {summary.transcript_id && (
          <section className="border-t pt-4">
            <a
              href={`#/responses/${responseId}/chat`}
              className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-800 font-medium"
            >
              📝 Просмотреть полный транскрипт диалога
              <span>→</span>
            </a>
          </section>
        )}
      </div>
    </div>
  )
}

