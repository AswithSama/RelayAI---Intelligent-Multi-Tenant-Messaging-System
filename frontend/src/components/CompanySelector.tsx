import { Building2, ChevronDown } from "lucide-react";
import type { Company } from "../api";

interface CompanySelectorProps {
  companies: Company[];
  value: number | null;
  onChange: (id: number | null) => void;
}

export function CompanySelector({
  companies,
  value,
  onChange,
}: CompanySelectorProps) {
  return (
    <label className="company-selector">
      <span className="field-label">Company Workspace</span>

      <span className="select-shell">
        <Building2 size={18} aria-hidden="true" />

        <select
          value={value ?? ""}
          onChange={(e) =>
            onChange(e.target.value === "" ? null : Number(e.target.value))
          }
        >
          <option value="">Select a company</option>

          {companies.map((company) => (
            <option key={company.id} value={company.id}>
              {company.name}
            </option>
          ))}
        </select>

        <ChevronDown
          size={17}
          aria-hidden="true"
          className="select-chevron"
        />
      </span>
    </label>
  );
}