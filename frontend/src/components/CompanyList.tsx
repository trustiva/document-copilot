export type Company = {
  ticker: string
  name: string
  cik?: string
}

type CompanyListProps = {
  companies: Company[]
  onSelect?: (company: Company) => void
}

export default function CompanyList({ companies, onSelect }: CompanyListProps) {
  if (companies.length === 0) {
    return <p className="text-sm text-gray-500">No companies found.</p>
  }

  return (
    <div className="mt-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-3">Tracked Companies</h2>
      <ul className="divide-y divide-gray-200 rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden">
        {companies.map((company) => (
          <li
            key={company.ticker}
            onClick={() => onSelect?.(company)}
            className="flex items-center justify-between p-4 hover:bg-gray-50 transition-colors cursor-pointer"
          >
            <div>
              <span className="font-semibold text-gray-900">{company.ticker}</span>
              <span className="ml-3 text-sm text-gray-600">{company.name}</span>
            </div>
            {company.cik && (
              <span className="rounded bg-gray-100 px-2 py-1 text-xs font-mono text-gray-600">
                CIK {company.cik}
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
