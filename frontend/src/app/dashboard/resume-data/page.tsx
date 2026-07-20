"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Braces,
  Copy,
  Download,
  FilePlus2,
  Loader2,
  Pencil,
  Plus,
  RefreshCw,
  Save,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { DashboardFrame } from "@/components/dashboard/dashboard-frame";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  deleteResume,
  downloadMaskedResume,
  downloadMaskedResumesArchive,
  downloadResumeDataReport,
  listJobs,
  listResumes,
  listStructuredResumes,
  parseResume,
  updateResume,
  updateStructuredResume,
  uploadResume,
  type Job,
  type ResumeListItem,
  type StructuredResumeData,
  type StructuredResumeEducation,
  type StructuredResumeExperience,
  type StructuredResumeRow,
} from "@/lib/api";

type MainTab = "data" | "uploads";
type SectionTab = "profile" | "skills" | "experience" | "education" | "certifications" | "json";

const mainTabs: Array<{ id: MainTab; label: string }> = [
  { id: "data", label: "Resume data" },
  { id: "uploads", label: "Uploaded resumes" },
];

const sectionTabs: Array<{ id: SectionTab; label: string }> = [
  { id: "profile", label: "Profile" },
  { id: "skills", label: "Skills" },
  { id: "experience", label: "Experience" },
  { id: "education", label: "Education" },
  { id: "certifications", label: "Certifications" },
  { id: "json", label: "JSON" },
];

const inputClass =
  "h-10 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-400";
const textareaClass =
  "min-h-28 w-full resize-y rounded-xl border border-slate-700 bg-slate-950 p-3 text-sm leading-6 text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-400";
const compactButtonClass = "h-8 px-3";

function formatDate(value?: string | null) {
  if (!value) return "Unknown";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
}

function joinList(values: string[], emptyLabel = "Not found") {
  return values.filter(Boolean).join(", ") || emptyLabel;
}

function formatExperience(items: StructuredResumeExperience[]) {
  if (!items.length) return "Not found";
  return items
    .map((item) => {
      const role = [item.title, item.company].filter(Boolean).join(" at ");
      const dates = [item.start_date, item.end_date].filter(Boolean).join(" - ");
      return [role, dates].filter(Boolean).join(" | ") || item.description;
    })
    .filter(Boolean)
    .join("; ");
}

function formatEducation(items: StructuredResumeEducation[]) {
  if (!items.length) return "Not found";
  return items
    .map((item) => [item.degree, item.institution, item.graduation_date].filter(Boolean).join(" | "))
    .filter(Boolean)
    .join("; ");
}

function searchableText(row: StructuredResumeRow) {
  const data = row.structured;
  return [
    row.resume_title,
    data.name,
    data.email,
    data.phone,
    data.location,
    data.linkedin,
    data.summary,
    data.skills.join(" "),
    formatExperience(data.experience),
    formatEducation(data.education),
    data.certifications.join(" "),
  ]
    .join(" ")
    .toLowerCase();
}

function uploadedSearchText(row: ResumeListItem) {
  return [row.title, row.source, row.status, row.candidate_name, row.candidate_email].join(" ").toLowerCase();
}

function linkedInHref(value: string) {
  if (!value) return "";
  return value.startsWith("http") ? value : `https://${value}`;
}

function emptyStructuredResume(): StructuredResumeData {
  return {
    name: "",
    email: "",
    phone: "",
    location: "",
    linkedin: "",
    summary: "",
    skills: [],
    experience: [],
    education: [],
    certifications: [],
  };
}

function cloneStructuredResume(data: StructuredResumeData): StructuredResumeData {
  return {
    ...data,
    skills: [...data.skills],
    experience: data.experience.map((item) => ({ ...item })),
    education: data.education.map((item) => ({ ...item })),
    certifications: [...data.certifications],
  };
}

function emptyExperience(): StructuredResumeExperience {
  return { company: "", title: "", start_date: "", end_date: "", location: "", description: "" };
}

function emptyEducation(): StructuredResumeEducation {
  return { institution: "", degree: "", field: "", graduation_date: "", gpa: "" };
}

function Field({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="space-y-2">
      <span className="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">{label}</span>
      <input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className={inputClass} />
    </label>
  );
}

function TextAreaField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="space-y-2">
      <span className="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">{label}</span>
      <textarea value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className={textareaClass} />
    </label>
  );
}

export default function ResumeDataPage() {
  const [activeMainTab, setActiveMainTab] = useState<MainTab>("data");
  const [activeSectionTab, setActiveSectionTab] = useState<SectionTab>("profile");
  const [rows, setRows] = useState<StructuredResumeRow[]>([]);
  const [uploadedResumes, setUploadedResumes] = useState<ResumeListItem[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [selectedJobId, setSelectedJobId] = useState("");
  const [query, setQuery] = useState("");
  const [uploadQuery, setUploadQuery] = useState("");
  const [loadingRows, setLoadingRows] = useState(true);
  const [loadingUploads, setLoadingUploads] = useState(true);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [copyStatus, setCopyStatus] = useState("");
  const [draft, setDraft] = useState<StructuredResumeData>(() => emptyStructuredResume());
  const [jsonDraft, setJsonDraft] = useState("");
  const [uploadDrafts, setUploadDrafts] = useState<Record<string, { title: string; source: string }>>({});
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [uploadInputKey, setUploadInputKey] = useState(0);
  const [candidateId, setCandidateId] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isReparsing, setIsReparsing] = useState(false);
  const [deletingId, setDeletingId] = useState("");
  const [savingUploadId, setSavingUploadId] = useState("");
  const [reparsingUploadId, setReparsingUploadId] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [isDownloadingMaskedArchive, setIsDownloadingMaskedArchive] = useState(false);
  const [maskedDownloadingId, setMaskedDownloadingId] = useState("");

  async function loadRows(showLoader = true) {
    if (showLoader) setLoadingRows(true);
    try {
      const data = await listStructuredResumes();
      setRows(data);
      setSelectedId((current) => (current && data.some((row) => row.resume_id === current) ? current : data[0]?.resume_id || ""));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load structured resume data.");
    } finally {
      if (showLoader) setLoadingRows(false);
    }
  }

  async function loadUploadedResumes(showLoader = true) {
    if (showLoader) setLoadingUploads(true);
    try {
      const data = await listResumes();
      setUploadedResumes(data);
      setUploadDrafts((current) => {
        const next: Record<string, { title: string; source: string }> = {};
        for (const resume of data) {
          next[resume.resume_id] = current[resume.resume_id] ?? {
            title: resume.title || "",
            source: resume.source || "",
          };
        }
        return next;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load uploaded resumes.");
    } finally {
      if (showLoader) setLoadingUploads(false);
    }
  }

  async function loadJobs() {
    setLoadingJobs(true);
    try {
      const data = await listJobs();
      setJobs(data);
      setSelectedJobId((current) => current || data.find((job) => job.status === "published")?.id || data[0]?.id || "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load jobs for ATS scoring.");
    } finally {
      setLoadingJobs(false);
    }
  }

  useEffect(() => {
    loadRows();
    loadUploadedResumes();
    loadJobs();
  }, []);

  const filteredRows = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return rows;
    return rows.filter((row) => searchableText(row).includes(normalized));
  }, [query, rows]);

  const filteredUploads = useMemo(() => {
    const normalized = uploadQuery.trim().toLowerCase();
    if (!normalized) return uploadedResumes;
    return uploadedResumes.filter((row) => uploadedSearchText(row).includes(normalized));
  }, [uploadQuery, uploadedResumes]);

  const selectedRow = useMemo(() => {
    return rows.find((row) => row.resume_id === selectedId) ?? filteredRows[0] ?? null;
  }, [filteredRows, rows, selectedId]);

  const selectedJson = JSON.stringify(selectedRow?.structured ?? emptyStructuredResume(), null, 2);

  useEffect(() => {
    const nextDraft = selectedRow?.structured ? cloneStructuredResume(selectedRow.structured) : emptyStructuredResume();
    setDraft(nextDraft);
    setJsonDraft(JSON.stringify(nextDraft, null, 2));
  }, [selectedJson, selectedRow?.resume_id]);

  function setProfileField(field: keyof Pick<StructuredResumeData, "name" | "email" | "phone" | "location" | "linkedin" | "summary">, value: string) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  function setSkill(index: number, value: string) {
    setDraft((current) => ({
      ...current,
      skills: current.skills.map((skill, itemIndex) => (itemIndex === index ? value : skill)),
    }));
  }

  function addSkill() {
    setDraft((current) => ({ ...current, skills: [...current.skills, ""] }));
  }

  function removeSkill(index: number) {
    setDraft((current) => ({ ...current, skills: current.skills.filter((_, itemIndex) => itemIndex !== index) }));
  }

  function setCertification(index: number, value: string) {
    setDraft((current) => ({
      ...current,
      certifications: current.certifications.map((certification, itemIndex) => (itemIndex === index ? value : certification)),
    }));
  }

  function addCertification() {
    setDraft((current) => ({ ...current, certifications: [...current.certifications, ""] }));
  }

  function removeCertification(index: number) {
    setDraft((current) => ({
      ...current,
      certifications: current.certifications.filter((_, itemIndex) => itemIndex !== index),
    }));
  }

  function setExperienceField(index: number, field: keyof StructuredResumeExperience, value: string) {
    setDraft((current) => ({
      ...current,
      experience: current.experience.map((item, itemIndex) => (itemIndex === index ? { ...item, [field]: value } : item)),
    }));
  }

  function addExperience() {
    setDraft((current) => ({ ...current, experience: [...current.experience, emptyExperience()] }));
  }

  function removeExperience(index: number) {
    setDraft((current) => ({ ...current, experience: current.experience.filter((_, itemIndex) => itemIndex !== index) }));
  }

  function setEducationField(index: number, field: keyof StructuredResumeEducation, value: string) {
    setDraft((current) => ({
      ...current,
      education: current.education.map((item, itemIndex) => (itemIndex === index ? { ...item, [field]: value } : item)),
    }));
  }

  function addEducation() {
    setDraft((current) => ({ ...current, education: [...current.education, emptyEducation()] }));
  }

  function removeEducation(index: number) {
    setDraft((current) => ({ ...current, education: current.education.filter((_, itemIndex) => itemIndex !== index) }));
  }

  async function saveStructuredDraft(payload: StructuredResumeData, message = "Resume data saved.") {
    if (!selectedRow) return;
    setError("");
    setSuccess("");
    setIsSaving(true);

    try {
      const cleaned = {
        ...payload,
        skills: payload.skills.map((item) => item.trim()).filter(Boolean),
        certifications: payload.certifications.map((item) => item.trim()).filter(Boolean),
      };
      const updated = await updateStructuredResume(selectedRow.resume_id, cleaned);
      setRows((current) => current.map((row) => (row.resume_id === updated.resume_id ? updated : row)));
      setDraft(cloneStructuredResume(updated.structured));
      setJsonDraft(JSON.stringify(updated.structured, null, 2));
      await loadUploadedResumes(false);
      setSuccess(message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save resume data.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleSaveCurrentSection() {
    await saveStructuredDraft(draft, "Resume section saved.");
  }

  async function handleCopyJson() {
    setCopyStatus("");
    try {
      await navigator.clipboard.writeText(jsonDraft);
      setCopyStatus("Copied");
      window.setTimeout(() => setCopyStatus(""), 1800);
    } catch {
      setError("Unable to copy JSON from this browser session.");
    }
  }

  async function handleSaveJson() {
    try {
      const parsed = JSON.parse(jsonDraft) as StructuredResumeData;
      await saveStructuredDraft(parsed, "Structured JSON saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid JSON.");
    }
  }

  async function handleReparseSelected() {
    if (!selectedRow) return;
    setError("");
    setSuccess("");
    setIsReparsing(true);

    try {
      await parseResume(selectedRow.resume_id, true);
      await loadRows(false);
      await loadUploadedResumes(false);
      setSuccess("Resume re-parsed from the uploaded file.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to re-parse resume.");
    } finally {
      setIsReparsing(false);
    }
  }

  async function handleDeleteResume(resumeId: string) {
    const target = uploadedResumes.find((resume) => resume.resume_id === resumeId)?.title ?? selectedRow?.resume_title ?? "this resume";
    if (!window.confirm(`Delete ${target}?`)) return;
    setError("");
    setSuccess("");
    setDeletingId(resumeId);

    try {
      await deleteResume(resumeId);
      setRows((current) => current.filter((row) => row.resume_id !== resumeId));
      setUploadedResumes((current) => current.filter((resume) => resume.resume_id !== resumeId));
      setSelectedId((current) => (current === resumeId ? "" : current));
      setSuccess("Resume deleted.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete resume.");
    } finally {
      setDeletingId("");
    }
  }

  function saveDownload(blob: Blob, fileName: string) {
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = fileName;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  async function handleDownloadExcel() {
    setError("");
    setSuccess("");
    setIsDownloading(true);

    try {
      const { blob, fileName } = await downloadResumeDataReport(selectedJobId || undefined);
      saveDownload(blob, fileName);
      setSuccess("Resume data Excel report downloaded.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to download resume data Excel report.");
    } finally {
      setIsDownloading(false);
    }
  }

  async function handleDownloadMaskedArchive() {
    setError("");
    setSuccess("");
    setIsDownloadingMaskedArchive(true);

    try {
      const { blob, fileName } = await downloadMaskedResumesArchive();
      saveDownload(blob, fileName);
      setSuccess("Masked resume ZIP downloaded.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to download masked resumes.");
    } finally {
      setIsDownloadingMaskedArchive(false);
    }
  }

  async function handleDownloadMaskedResume(resumeId: string) {
    setError("");
    setSuccess("");
    setMaskedDownloadingId(resumeId);

    try {
      const { blob, fileName } = await downloadMaskedResume(resumeId);
      saveDownload(blob, fileName);
      setSuccess("Masked resume PDF downloaded.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to download masked resume.");
    } finally {
      setMaskedDownloadingId("");
    }
  }

  async function handleUploadResumes() {
    if (!uploadFiles.length) {
      setError("Choose at least one resume file to upload.");
      return;
    }
    setError("");
    setSuccess("");
    setIsUploading(true);

    try {
      for (const file of uploadFiles) {
        await uploadResume(file, candidateId.trim() || undefined);
      }
      setUploadFiles([]);
      setUploadInputKey((current) => current + 1);
      setCandidateId("");
      await loadUploadedResumes(false);
      await loadRows(false);
      setSuccess("Resume upload completed.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to upload resumes.");
    } finally {
      setIsUploading(false);
    }
  }

  async function handleSaveUploadedResume(resume: ResumeListItem) {
    const draftRow = uploadDrafts[resume.resume_id] ?? { title: resume.title || "", source: resume.source || "" };
    setError("");
    setSuccess("");
    setSavingUploadId(resume.resume_id);

    try {
      const updated = await updateResume(resume.resume_id, {
        title: draftRow.title,
        source: draftRow.source || null,
      });
      setUploadedResumes((current) => current.map((item) => (item.resume_id === updated.resume_id ? updated : item)));
      setRows((current) =>
        current.map((row) => (row.resume_id === updated.resume_id ? { ...row, resume_title: updated.title } : row)),
      );
      setSuccess("Uploaded resume saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save uploaded resume.");
    } finally {
      setSavingUploadId("");
    }
  }

  async function handleParseUploadedResume(resume: ResumeListItem, force: boolean) {
    setError("");
    setSuccess("");
    setReparsingUploadId(resume.resume_id);

    try {
      await parseResume(resume.resume_id, force);
      setSelectedId(resume.resume_id);
      await loadUploadedResumes(false);
      await loadRows(false);
      setActiveMainTab("data");
      setSuccess(force ? "Resume re-parsed." : "Resume parsed.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to parse resume.");
    } finally {
      setReparsingUploadId("");
    }
  }

  function renderProfileEditor() {
    return (
      <div className="grid gap-4 lg:grid-cols-2">
        <Field label="Candidate name" value={draft.name} onChange={(value) => setProfileField("name", value)} />
        <Field label="Email" value={draft.email} onChange={(value) => setProfileField("email", value)} />
        <Field label="Phone" value={draft.phone} onChange={(value) => setProfileField("phone", value)} />
        <Field label="Location" value={draft.location} onChange={(value) => setProfileField("location", value)} />
        <div className="lg:col-span-2">
          <Field label="LinkedIn" value={draft.linkedin} onChange={(value) => setProfileField("linkedin", value)} />
        </div>
        <div className="lg:col-span-2">
          <TextAreaField label="Summary" value={draft.summary} onChange={(value) => setProfileField("summary", value)} />
        </div>
      </div>
    );
  }

  function renderSkillsEditor() {
    return (
      <div className="space-y-3">
        {draft.skills.map((skill, index) => (
          <div key={`skill-${index}`} className="flex gap-2">
            <input value={skill} onChange={(event) => setSkill(index, event.target.value)} className={inputClass} />
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className={compactButtonClass}
              aria-label={`Remove skill ${index + 1}`}
              onClick={() => removeSkill(index)}
            >
              <X className="mr-1 h-4 w-4" />
              Remove
            </Button>
          </div>
        ))}
        <Button type="button" variant="secondary" size="sm" onClick={addSkill}>
          <Plus className="mr-2 h-4 w-4" />
          Add skill
        </Button>
      </div>
    );
  }

  function renderExperienceEditor() {
    return (
      <div className="space-y-4">
        {draft.experience.map((item, index) => (
          <div key={`experience-${index}`} className="border border-slate-800 bg-slate-950/50 p-4">
            <div className="mb-4 flex items-center justify-between gap-3">
              <p className="text-sm font-semibold text-white">Experience {index + 1}</p>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                className={compactButtonClass}
                aria-label={`Remove experience ${index + 1}`}
                onClick={() => removeExperience(index)}
              >
                <Trash2 className="mr-1 h-4 w-4" />
                Remove
              </Button>
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <Field label="Company" value={item.company} onChange={(value) => setExperienceField(index, "company", value)} />
              <Field label="Title" value={item.title} onChange={(value) => setExperienceField(index, "title", value)} />
              <Field label="Start date" value={item.start_date} onChange={(value) => setExperienceField(index, "start_date", value)} />
              <Field label="End date" value={item.end_date} onChange={(value) => setExperienceField(index, "end_date", value)} />
              <div className="lg:col-span-2">
                <Field label="Location" value={item.location} onChange={(value) => setExperienceField(index, "location", value)} />
              </div>
              <div className="lg:col-span-2">
                <TextAreaField label="Description" value={item.description} onChange={(value) => setExperienceField(index, "description", value)} />
              </div>
            </div>
          </div>
        ))}
        <Button type="button" variant="secondary" size="sm" onClick={addExperience}>
          <Plus className="mr-2 h-4 w-4" />
          Add experience
        </Button>
      </div>
    );
  }

  function renderEducationEditor() {
    return (
      <div className="space-y-4">
        {draft.education.map((item, index) => (
          <div key={`education-${index}`} className="border border-slate-800 bg-slate-950/50 p-4">
            <div className="mb-4 flex items-center justify-between gap-3">
              <p className="text-sm font-semibold text-white">Education {index + 1}</p>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                className={compactButtonClass}
                aria-label={`Remove education ${index + 1}`}
                onClick={() => removeEducation(index)}
              >
                <Trash2 className="mr-1 h-4 w-4" />
                Remove
              </Button>
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <Field label="Institution" value={item.institution} onChange={(value) => setEducationField(index, "institution", value)} />
              <Field label="Degree" value={item.degree} onChange={(value) => setEducationField(index, "degree", value)} />
              <Field label="Field" value={item.field} onChange={(value) => setEducationField(index, "field", value)} />
              <Field label="Graduation date" value={item.graduation_date} onChange={(value) => setEducationField(index, "graduation_date", value)} />
              <div className="lg:col-span-2">
                <Field label="GPA" value={item.gpa} onChange={(value) => setEducationField(index, "gpa", value)} />
              </div>
            </div>
          </div>
        ))}
        <Button type="button" variant="secondary" size="sm" onClick={addEducation}>
          <Plus className="mr-2 h-4 w-4" />
          Add education
        </Button>
      </div>
    );
  }

  function renderCertificationsEditor() {
    return (
      <div className="space-y-3">
        {draft.certifications.map((certification, index) => (
          <div key={`certification-${index}`} className="flex gap-2">
            <input value={certification} onChange={(event) => setCertification(index, event.target.value)} className={inputClass} />
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className={compactButtonClass}
              aria-label={`Remove certification ${index + 1}`}
              onClick={() => removeCertification(index)}
            >
              <X className="mr-1 h-4 w-4" />
              Remove
            </Button>
          </div>
        ))}
        <Button type="button" variant="secondary" size="sm" onClick={addCertification}>
          <Plus className="mr-2 h-4 w-4" />
          Add certification
        </Button>
      </div>
    );
  }

  function renderJsonEditor() {
    return (
      <div className="space-y-3">
        <textarea
          value={jsonDraft}
          onChange={(event) => setJsonDraft(event.target.value)}
          spellCheck={false}
          className="min-h-[520px] w-full resize-y border border-slate-800 bg-slate-950 p-4 font-mono text-xs leading-6 text-slate-200 outline-none transition focus:border-cyan-400"
        />
        <div className="flex items-center gap-3">
          {copyStatus ? <span className="text-sm text-emerald-300">{copyStatus}</span> : null}
          <Button type="button" variant="secondary" size="sm" onClick={handleCopyJson} disabled={!selectedRow}>
            <Copy className="mr-2 h-4 w-4" />
            Copy JSON
          </Button>
          <Button type="button" size="sm" onClick={handleSaveJson} disabled={!selectedRow || isSaving}>
            {isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
            Save JSON
          </Button>
        </div>
      </div>
    );
  }

  function renderSectionEditor() {
    if (!selectedRow) {
      return <div className="border border-dashed border-slate-700 bg-slate-950/50 p-6 text-center text-sm text-slate-400">No parsed resume selected.</div>;
    }
    if (activeSectionTab === "profile") return renderProfileEditor();
    if (activeSectionTab === "skills") return renderSkillsEditor();
    if (activeSectionTab === "experience") return renderExperienceEditor();
    if (activeSectionTab === "education") return renderEducationEditor();
    if (activeSectionTab === "certifications") return renderCertificationsEditor();
    return renderJsonEditor();
  }

  return (
    <DashboardFrame
      title="Resume data"
      description="Review parsed fields, uploaded files, and recruiter edits from one workspace."
      showRightPanel={false}
    >
      <div className="space-y-6">
        <div className="flex flex-col gap-4 rounded-3xl border border-slate-800 bg-slate-900/90 p-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-wrap gap-2">
            {mainTabs.map((tab) => (
              <Button key={tab.id} type="button" variant={activeMainTab === tab.id ? "default" : "secondary"} onClick={() => setActiveMainTab(tab.id)}>
                {tab.label}
              </Button>
            ))}
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <select
              value={selectedJobId}
              onChange={(event) => setSelectedJobId(event.target.value)}
              disabled={loadingJobs}
              className="h-10 min-w-64 rounded-full border border-slate-700 bg-slate-950 px-4 text-sm text-white outline-none transition focus:border-cyan-400"
            >
              {!jobs.length ? <option value="">No jobs found</option> : null}
              {jobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.title}
                </option>
              ))}
            </select>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={handleDownloadMaskedArchive}
              disabled={isDownloadingMaskedArchive || loadingRows || !rows.length}
            >
              {isDownloadingMaskedArchive ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
              Masked ZIP
            </Button>
            <Button type="button" size="sm" onClick={handleDownloadExcel} disabled={isDownloading || loadingRows || loadingJobs || !rows.length || !selectedJobId}>
              {isDownloading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
              Download Excel
            </Button>
          </div>
        </div>

        {error ? <Alert className="border-rose-400/40 bg-rose-950/30 text-rose-100">{error}</Alert> : null}
        {success ? <Alert className="border-emerald-400/40 bg-emerald-950/30 text-emerald-100">{success}</Alert> : null}

        {activeMainTab === "data" ? (
          <>
            <section className="rounded-3xl border border-slate-800 bg-slate-900/90">
              <div className="flex flex-col gap-4 border-b border-slate-800 px-6 py-5 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <p className="text-sm uppercase tracking-[0.35em] text-slate-400">Parsed records</p>
                  <h2 className="mt-2 text-xl font-semibold text-white">Resume data table</h2>
                </div>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                  <div className="relative">
                    <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                    <input
                      value={query}
                      onChange={(event) => setQuery(event.target.value)}
                      placeholder="Search parsed data"
                      className="h-10 w-full rounded-full border border-slate-700 bg-slate-950 pl-9 pr-4 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-400 sm:w-72"
                    />
                  </div>
                  <span className="rounded-full border border-slate-700 bg-slate-950 px-3 py-1 text-xs text-slate-300">
                    {filteredRows.length} resume{filteredRows.length === 1 ? "" : "s"}
                  </span>
                  <Button type="button" variant="secondary" size="sm" onClick={() => loadRows()} disabled={loadingRows}>
                    {loadingRows ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
                    Refresh
                  </Button>
                </div>
              </div>

              <div className="space-y-4 p-6">
                {loadingRows ? (
                  <div className="flex items-center gap-2 border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
                    <Loader2 className="h-4 w-4 animate-spin text-cyan-300" />
                    Loading structured resume data
                  </div>
                ) : null}

                {!loadingRows && !filteredRows.length ? (
                  <div className="border border-dashed border-slate-700 bg-slate-950/50 p-6 text-center text-sm text-slate-400">
                    No structured resume data found.
                  </div>
                ) : null}

                {filteredRows.length ? (
                  <div className="overflow-x-auto border border-slate-800">
                    <table className="w-full min-w-[1600px] border-collapse text-left text-sm">
                      <thead className="bg-slate-950 text-xs uppercase tracking-[0.22em] text-slate-500">
                        <tr>
                          <th className="px-4 py-3 font-medium">Resume</th>
                          <th className="px-4 py-3 font-medium">Name</th>
                          <th className="px-4 py-3 font-medium">Email</th>
                          <th className="px-4 py-3 font-medium">Phone</th>
                          <th className="px-4 py-3 font-medium">Location</th>
                          <th className="px-4 py-3 font-medium">LinkedIn</th>
                          <th className="px-4 py-3 font-medium">Summary</th>
                          <th className="px-4 py-3 font-medium">Skills</th>
                          <th className="px-4 py-3 font-medium">Experience</th>
                          <th className="px-4 py-3 font-medium">Education</th>
                          <th className="px-4 py-3 font-medium">Certifications</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800 bg-slate-950/40">
                        {filteredRows.map((row) => {
                          const data = row.structured;
                          const active = selectedRow?.resume_id === row.resume_id;
                          return (
                            <tr
                              key={row.resume_id}
                              className={`align-top transition ${active ? "bg-cyan-500/10" : "hover:bg-slate-900/70"}`}
                              onClick={() => setSelectedId(row.resume_id)}
                            >
                              <td className="px-4 py-4">
                                <p className="max-w-48 font-medium text-white">{row.resume_title || "Untitled resume"}</p>
                                <p className="mt-1 text-xs text-slate-500">{formatDate(row.created_at)}</p>
                                <Button
                                  type="button"
                                  size="sm"
                                  variant="ghost"
                                  className="mt-2 h-8 px-0 text-cyan-300 hover:text-cyan-200"
                                  onClick={(event) => {
                                    event.stopPropagation();
                                    setSelectedId(row.resume_id);
                                    setActiveSectionTab("profile");
                                  }}
                                >
                                  <Pencil className="mr-1 h-4 w-4" />
                                  Edit
                                </Button>
                                <Button
                                  type="button"
                                  size="sm"
                                  variant="ghost"
                                  className="mt-1 h-8 px-0 text-cyan-300 hover:text-cyan-200"
                                  onClick={(event) => {
                                    event.stopPropagation();
                                    handleDownloadMaskedResume(row.resume_id);
                                  }}
                                  disabled={maskedDownloadingId === row.resume_id}
                                >
                                  {maskedDownloadingId === row.resume_id ? (
                                    <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                                  ) : (
                                    <Download className="mr-1 h-4 w-4" />
                                  )}
                                  Masked PDF
                                </Button>
                              </td>
                              <td className="px-4 py-4 font-medium text-slate-100">{data.name || "Not found"}</td>
                              <td className="px-4 py-4 text-slate-300">{data.email || "Not found"}</td>
                              <td className="px-4 py-4 text-slate-300">{data.phone || "Not found"}</td>
                              <td className="px-4 py-4 text-slate-300">{data.location || "Not found"}</td>
                              <td className="px-4 py-4">
                                {data.linkedin ? (
                                  <a href={linkedInHref(data.linkedin)} className="text-cyan-300 hover:text-cyan-200" target="_blank" rel="noreferrer">
                                    {data.linkedin}
                                  </a>
                                ) : (
                                  <span className="text-slate-500">Not found</span>
                                )}
                              </td>
                              <td className="px-4 py-4">
                                <p className="max-h-24 max-w-80 overflow-hidden text-slate-300">{data.summary || "Not found"}</p>
                              </td>
                              <td className="px-4 py-4">
                                <p className="max-h-24 max-w-72 overflow-hidden text-slate-300">{joinList(data.skills)}</p>
                              </td>
                              <td className="px-4 py-4">
                                <p className="max-h-24 max-w-80 overflow-hidden text-slate-300">{formatExperience(data.experience)}</p>
                              </td>
                              <td className="px-4 py-4">
                                <p className="max-h-24 max-w-80 overflow-hidden text-slate-300">{formatEducation(data.education)}</p>
                              </td>
                              <td className="px-4 py-4">
                                <p className="max-h-24 max-w-72 overflow-hidden text-slate-300">{joinList(data.certifications)}</p>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                ) : null}
              </div>
            </section>

            <section className="rounded-3xl border border-slate-800 bg-slate-900/90">
              <div className="flex flex-col gap-4 border-b border-slate-800 px-6 py-5 xl:flex-row xl:items-center xl:justify-between">
                <div>
                  <p className="text-sm uppercase tracking-[0.35em] text-slate-400">Section editor</p>
                  <h2 className="mt-2 text-xl font-semibold text-white">{selectedRow?.structured.name || selectedRow?.resume_title || "Select a resume"}</h2>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <Button type="button" variant="secondary" size="sm" onClick={handleReparseSelected} disabled={!selectedRow || isReparsing}>
                    {isReparsing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
                    Re-parse
                  </Button>
                  <Button type="button" size="sm" onClick={handleSaveCurrentSection} disabled={!selectedRow || isSaving || activeSectionTab === "json"}>
                    {isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                    Save section
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={() => selectedRow && handleDownloadMaskedResume(selectedRow.resume_id)}
                    disabled={!selectedRow || maskedDownloadingId === selectedRow?.resume_id}
                  >
                    {maskedDownloadingId === selectedRow?.resume_id ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
                    Masked PDF
                  </Button>
                  <Button type="button" variant="secondary" size="sm" onClick={() => selectedRow && handleDeleteResume(selectedRow.resume_id)} disabled={!selectedRow || deletingId === selectedRow?.resume_id}>
                    {deletingId === selectedRow?.resume_id ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Trash2 className="mr-2 h-4 w-4" />}
                    Delete
                  </Button>
                </div>
              </div>

              <div className="space-y-5 p-6">
                <div className="flex flex-wrap gap-2">
                  {sectionTabs.map((tab) => (
                    <Button key={tab.id} type="button" variant={activeSectionTab === tab.id ? "default" : "secondary"} size="sm" onClick={() => setActiveSectionTab(tab.id)}>
                      {tab.id === "json" ? <Braces className="mr-2 h-4 w-4" /> : null}
                      {tab.label}
                    </Button>
                  ))}
                </div>
                {renderSectionEditor()}
              </div>
            </section>
          </>
        ) : (
          <section className="rounded-3xl border border-slate-800 bg-slate-900/90">
            <div className="flex flex-col gap-4 border-b border-slate-800 px-6 py-5 xl:flex-row xl:items-center xl:justify-between">
              <div>
                <p className="text-sm uppercase tracking-[0.35em] text-slate-400">File records</p>
                <h2 className="mt-2 text-xl font-semibold text-white">Uploaded resumes</h2>
              </div>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                  <input
                    value={uploadQuery}
                    onChange={(event) => setUploadQuery(event.target.value)}
                    placeholder="Search uploads"
                    className="h-10 w-full rounded-full border border-slate-700 bg-slate-950 pl-9 pr-4 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-400 sm:w-72"
                  />
                </div>
                <span className="rounded-full border border-slate-700 bg-slate-950 px-3 py-1 text-xs text-slate-300">
                  {filteredUploads.length} upload{filteredUploads.length === 1 ? "" : "s"}
                </span>
                <Button type="button" variant="secondary" size="sm" onClick={() => loadUploadedResumes()} disabled={loadingUploads}>
                  {loadingUploads ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
                  Refresh
                </Button>
              </div>
            </div>

            <div className="space-y-5 p-6">
              <div className="grid gap-4 border border-slate-800 bg-slate-950/50 p-4 xl:grid-cols-[1.3fr_0.8fr_auto] xl:items-end">
                <label className="space-y-2">
                  <span className="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">Resume files</span>
                  <input
                    key={uploadInputKey}
                    type="file"
                    multiple
                    onChange={(event) => setUploadFiles(Array.from(event.target.files ?? []))}
                    className="block w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-300 file:mr-4 file:rounded-full file:border-0 file:bg-cyan-500 file:px-4 file:py-2 file:text-sm file:font-medium file:text-slate-950 hover:file:bg-cyan-400"
                  />
                </label>
                <Field label="Existing candidate ID" value={candidateId} onChange={setCandidateId} placeholder="Optional" />
                <Button type="button" onClick={handleUploadResumes} disabled={isUploading || !uploadFiles.length}>
                  {isUploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FilePlus2 className="mr-2 h-4 w-4" />}
                  Upload
                </Button>
              </div>

              {loadingUploads ? (
                <div className="flex items-center gap-2 border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
                  <Loader2 className="h-4 w-4 animate-spin text-cyan-300" />
                  Loading uploaded resumes
                </div>
              ) : null}

              {!loadingUploads && !filteredUploads.length ? (
                <div className="border border-dashed border-slate-700 bg-slate-950/50 p-6 text-center text-sm text-slate-400">
                  No uploaded resumes found.
                </div>
              ) : null}

              {filteredUploads.length ? (
                <div className="overflow-x-auto border border-slate-800">
                  <table className="w-full min-w-[1200px] border-collapse text-left text-sm">
                    <thead className="bg-slate-950 text-xs uppercase tracking-[0.22em] text-slate-500">
                      <tr>
                        <th className="px-4 py-3 font-medium">Resume</th>
                        <th className="px-4 py-3 font-medium">Source</th>
                        <th className="px-4 py-3 font-medium">Candidate</th>
                        <th className="px-4 py-3 font-medium">Status</th>
                        <th className="px-4 py-3 font-medium">Uploaded</th>
                        <th className="px-4 py-3 font-medium">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800 bg-slate-950/40">
                      {filteredUploads.map((resume) => {
                        const uploadDraft = uploadDrafts[resume.resume_id] ?? { title: resume.title || "", source: resume.source || "" };
                        const isParsed = Boolean(resume.current_version_id);
                        return (
                          <tr key={resume.resume_id} className="align-top">
                            <td className="px-4 py-4">
                              <input
                                value={uploadDraft.title}
                                onChange={(event) =>
                                  setUploadDrafts((current) => ({
                                    ...current,
                                    [resume.resume_id]: { ...uploadDraft, title: event.target.value },
                                  }))
                                }
                                className={inputClass}
                              />
                            </td>
                            <td className="px-4 py-4">
                              <input
                                value={uploadDraft.source}
                                onChange={(event) =>
                                  setUploadDrafts((current) => ({
                                    ...current,
                                    [resume.resume_id]: { ...uploadDraft, source: event.target.value },
                                  }))
                                }
                                className={inputClass}
                              />
                            </td>
                            <td className="px-4 py-4 text-slate-300">
                              <p className="font-medium text-slate-100">{resume.candidate_name || "Unknown"}</p>
                              <p className="mt-1 text-xs text-slate-500">{resume.candidate_email || "No email"}</p>
                            </td>
                            <td className="px-4 py-4">
                              <span className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-xs text-slate-300">{resume.status}</span>
                            </td>
                            <td className="px-4 py-4 text-slate-300">{formatDate(resume.created_at)}</td>
                            <td className="px-4 py-4">
                              <div className="flex flex-wrap gap-2">
                                <Button type="button" size="sm" onClick={() => handleSaveUploadedResume(resume)} disabled={savingUploadId === resume.resume_id}>
                                  {savingUploadId === resume.resume_id ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                                  Save
                                </Button>
                                <Button
                                  type="button"
                                  variant="secondary"
                                  size="sm"
                                  onClick={() => handleParseUploadedResume(resume, isParsed)}
                                  disabled={reparsingUploadId === resume.resume_id}
                                >
                                  {reparsingUploadId === resume.resume_id ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
                                  {isParsed ? "Re-parse" : "Parse"}
                                </Button>
                                {isParsed ? (
                                  <Button
                                    type="button"
                                    variant="secondary"
                                    size="sm"
                                    onClick={() => {
                                      setSelectedId(resume.resume_id);
                                      setActiveMainTab("data");
                                    }}
                                  >
                                    <Pencil className="mr-2 h-4 w-4" />
                                    Edit data
                                  </Button>
                                ) : null}
                                {isParsed ? (
                                  <Button
                                    type="button"
                                    variant="secondary"
                                    size="sm"
                                    onClick={() => handleDownloadMaskedResume(resume.resume_id)}
                                    disabled={maskedDownloadingId === resume.resume_id}
                                  >
                                    {maskedDownloadingId === resume.resume_id ? (
                                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    ) : (
                                      <Download className="mr-2 h-4 w-4" />
                                    )}
                                    Masked PDF
                                  </Button>
                                ) : null}
                                <Button type="button" variant="secondary" size="sm" onClick={() => handleDeleteResume(resume.resume_id)} disabled={deletingId === resume.resume_id}>
                                  {deletingId === resume.resume_id ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Trash2 className="mr-2 h-4 w-4" />}
                                  Delete
                                </Button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : null}
            </div>
          </section>
        )}
      </div>
    </DashboardFrame>
  );
}
