import React, { createContext, useContext, useMemo, useReducer, useEffect, useId } from "react";
import { createRoot } from "react-dom/client";

/**
 * ---------------------------
 * Config (no UI hardcoding)
 * ---------------------------
 * You can override these from Django template via:
 * window.__INVENTTECH_CONFIG__ = { endpoints: {...} }
 */
const CONFIG = {
  endpoints: {
    profileGet: "/api/profile/",
    profileSave: "/api/profile/save/",
    firmGet: "/api/firm/",
    firmSave: "/api/firm/save/",
  },
  ...window.__INVENTTECH_CONFIG__,
};

const FIRM_TYPE_OPTIONS = [
  { value: "law_firm", label: "Law Firm" },
  { value: "company", label: "Company" },
  { value: "individual", label: "Individual" },
  { value: "startup", label: "Startup" },
  { value: "other", label: "Other" },
];

const ROLE_OPTIONS = [
  { value: "owner_admin", label: "Owner / Admin" },
  { value: "manager", label: "Manager" },
  { value: "staff", label: "Staff" },
  { value: "viewer", label: "Viewer" },
];

/**
 * Scalable permission structure (we’re not enforcing yet, but this is ready).
 * UI/logic can reference these keys later across modules.
 */
const PERMISSION_KEYS = {
  FIRM_MANAGE: "firm:manage",
  USERS_MANAGE: "users:manage",
  RECORDS_CREATE: "records:create",
  RECORDS_EDIT: "records:edit",
  RECORDS_VIEW: "records:view",
  SETTINGS_EDIT: "settings:edit",
};

const ROLE_PERMISSIONS = {
  owner_admin: Object.values(PERMISSION_KEYS),
  manager: [
    PERMISSION_KEYS.FIRM_MANAGE,
    PERMISSION_KEYS.USERS_MANAGE,
    PERMISSION_KEYS.RECORDS_CREATE,
    PERMISSION_KEYS.RECORDS_EDIT,
    PERMISSION_KEYS.RECORDS_VIEW,
  ],
  staff: [
    PERMISSION_KEYS.RECORDS_CREATE,
    PERMISSION_KEYS.RECORDS_EDIT,
    PERMISSION_KEYS.RECORDS_VIEW,
  ],
  viewer: [PERMISSION_KEYS.RECORDS_VIEW],
};

/**
 * ---------------------------
 * Small API helper (CSRF)
 * ---------------------------
 */
function getCsrfToken() {
  // 1) explicit config
  if (CONFIG?.csrfToken) return CONFIG.csrfToken;

  // 2) Django CSRF cookie
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  if (match) return match[1];

  // 3) fallback: hidden input (if present somewhere)
  const el = document.querySelector('input[name="csrfmiddlewaretoken"]');
  return el?.value || "";
}

async function apiFetch(url, { method = "GET", body, headers = {} } = {}) {
  const finalHeaders = {
    "X-Requested-With": "XMLHttpRequest",
    ...headers,
  };

  if (method !== "GET") {
    finalHeaders["X-CSRFToken"] = getCsrfToken();
  }

  const res = await fetch(url, {
    method,
    headers: finalHeaders,
    body,
    credentials: "same-origin",
  });

  const contentType = res.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await res.json() : await res.text();

  if (!res.ok) {
    const message = typeof data === "string" ? data : data?.message || "Request failed";
    throw new Error(message);
  }

  return data;
}

/**
 * ---------------------------
 * Reusable Modal Component
 * ---------------------------
 */
function Modal({ open, title, subtitle, onClose, children, footer }) {
  if (!open) return null;

  return (
    <div
      className="modal-backdrop show"
      aria-hidden={!open}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose?.();
      }}
    >
      <div className="modal-card" role="dialog" aria-modal="true" aria-label={title}>
        <div className="modal-head">
          <div>
            <div className="modal-title">{title}</div>
            {subtitle ? <div className="modal-sub">{subtitle}</div> : null}
          </div>
          <button className="iconbtn" type="button" title="Close" onClick={onClose}>
            ✕
          </button>
        </div>

        {children}

        {footer ? <div className="modal-actions">{footer}</div> : null}
      </div>
    </div>
  );
}

/**
 * ---------------------------
 * App State (Context)
 * ---------------------------
 */
const AppContext = createContext(null);

const initialState = {
  firm: CONFIG?.initialFirm || null,
  profile: CONFIG?.initialProfile || {
    username: "",
    email: "",
    first_name: "",
    last_name: "",
    phone: "",
    address: "",
    role: "owner_admin",
  },
  ui: {
    profileOpen: false,
    firmOpen: false,
    toast: "",
    toastKind: "info",
  },
};

function reducer(state, action) {
  switch (action.type) {
    case "UI/OPEN_PROFILE":
      return { ...state, ui: { ...state.ui, profileOpen: true, toast: "" } };
    case "UI/CLOSE_PROFILE":
      return { ...state, ui: { ...state.ui, profileOpen: false } };
    case "UI/OPEN_FIRM":
      return { ...state, ui: { ...state.ui, firmOpen: true, toast: "" } };
    case "UI/CLOSE_FIRM":
      return { ...state, ui: { ...state.ui, firmOpen: false } };
    case "UI/TOAST":
      return { ...state, ui: { ...state.ui, toast: action.message || "", toastKind: action.kind || "info" } };

    case "FIRM/SET": {
      const firm = action.firm || null;
      // firm is single source of truth, and profile auto-references it
      return {
        ...state,
        firm,
        profile: {
          ...state.profile,
          firm_name: firm?.firm_name || firm?.name || "",
        },
      };
    }

    case "PROFILE/SET":
      return { ...state, profile: { ...state.profile, ...action.profile } };

    default:
      return state;
  }
}

function AppProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  const value = useMemo(() => {
    const role = state.profile?.role || "viewer";
    const permissions = ROLE_PERMISSIONS[role] || [];
    return { state, dispatch, permissions };
  }, [state]);

  // Optional: load firm/profile from backend on mount (endpoints are config-driven)
  useEffect(() => {
    (async () => {
      try {
        if (!CONFIG?.endpoints?.firmGet) return;
        const firmData = await apiFetch(CONFIG.endpoints.firmGet);
        if (firmData?.firm) dispatch({ type: "FIRM/SET", firm: firmData.firm });
      } catch {
        // ignore (works even if you haven't created endpoints yet)
      }

      try {
        if (!CONFIG?.endpoints?.profileGet) return;
        const profileData = await apiFetch(CONFIG.endpoints.profileGet);
        if (profileData?.profile) dispatch({ type: "PROFILE/SET", profile: profileData.profile });
      } catch {
        // ignore
      }
    })();
  }, []);

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used inside AppProvider");
  return ctx;
}

/**
 * ---------------------------
 * Firm Modal
 * ---------------------------
 */
function FirmModal() {
  const { state, dispatch } = useApp();
  const open = state.ui.firmOpen;

  const [draft, setDraft] = React.useState(() => ({
    firm_name: state.firm?.firm_name || "",
    firm_type: state.firm?.firm_type || "",
    registration_number: state.firm?.registration_number || "",
    gst_number: state.firm?.gst_number || "",
    email: state.firm?.email || "",
    phone: state.firm?.phone || "",
    address: state.firm?.address || "",
    city: state.firm?.city || "",
    state: state.firm?.state || "",
    country: state.firm?.country || "",
    website: state.firm?.website || "",
    created_at: state.firm?.created_at || "",
  }));

  // sync when opening
  useEffect(() => {
    if (!open) return;
    setDraft({
      firm_name: state.firm?.firm_name || "",
      firm_type: state.firm?.firm_type || "",
      registration_number: state.firm?.registration_number || "",
      gst_number: state.firm?.gst_number || "",
      email: state.firm?.email || "",
      phone: state.firm?.phone || "",
      address: state.firm?.address || "",
      city: state.firm?.city || "",
      state: state.firm?.state || "",
      country: state.firm?.country || "",
      website: state.firm?.website || "",
      created_at: state.firm?.created_at || "",
    });
  }, [open, state.firm]);

  const createdLabel = useMemo(() => {
    const d = draft.created_at ? new Date(draft.created_at) : new Date();
    return isNaN(d.getTime()) ? "" : d.toLocaleString();
  }, [draft.created_at]);

  function setField(key, value) {
    setDraft((p) => ({ ...p, [key]: value }));
  }

  async function onSave() {
    if (!draft.firm_name?.trim()) {
      dispatch({ type: "UI/TOAST", kind: "error", message: "Firm Name is required." });
      return;
    }
    if (!draft.firm_type) {
      dispatch({ type: "UI/TOAST", kind: "error", message: "Firm Type is required." });
      return;
    }

    try {
      dispatch({ type: "UI/TOAST", kind: "info", message: "Saving firm..." });

      // Send as JSON; backend should return { firm: {...} }
      const payload = JSON.stringify(draft);
      const data = await apiFetch(CONFIG.endpoints.firmSave, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: payload,
      });

      const firm = data?.firm || draft;
      dispatch({ type: "FIRM/SET", firm });
      dispatch({ type: "UI/TOAST", kind: "success", message: "Firm saved ✅" });

      setTimeout(() => {
        dispatch({ type: "UI/CLOSE_FIRM" });
        dispatch({ type: "UI/TOAST", message: "" });
      }, 600);
    } catch (e) {
      dispatch({ type: "UI/TOAST", kind: "error", message: e.message || "Error saving firm ❌" });
    }
  }

  return (
    <Modal
      open={open}
      title="Firm Details"
      subtitle="Create or update your firm information"
      onClose={() => dispatch({ type: "UI/CLOSE_FIRM" })}
      footer={
        <>
          <button className="btn btn-ghost" type="button" onClick={() => dispatch({ type: "UI/CLOSE_FIRM" })}>
            Cancel
          </button>
          <button className="btn btn-save" type="button" onClick={onSave}>
            Save
          </button>
        </>
      }
    >
      <div className="modal-grid">
        <div className="f full">
          <label>Firm Name *</label>
          <input value={draft.firm_name} onChange={(e) => setField("firm_name", e.target.value)} placeholder="Enter firm name" />
        </div>

        <div className="f">
          <label>Firm Type *</label>
          <select value={draft.firm_type} onChange={(e) => setField("firm_type", e.target.value)}>
            <option value="">Select</option>
            {FIRM_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className="f">
          <label>Registration Number</label>
          <input value={draft.registration_number} onChange={(e) => setField("registration_number", e.target.value)} placeholder="Optional" />
        </div>

        <div className="f">
          <label>GST Number (optional)</label>
          <input value={draft.gst_number} onChange={(e) => setField("gst_number", e.target.value)} placeholder="Optional" />
        </div>

        <div className="f">
          <label>Firm Email</label>
          <input value={draft.email} onChange={(e) => setField("email", e.target.value)} placeholder="name@firm.com" />
        </div>

        <div className="f">
          <label>Firm Phone Number</label>
          <input value={draft.phone} onChange={(e) => setField("phone", e.target.value)} placeholder="98XXXXXXXX" />
        </div>

        <div className="f full">
          <label>Firm Address</label>
          <textarea rows={3} value={draft.address} onChange={(e) => setField("address", e.target.value)} placeholder="Address line" />
        </div>

        <div className="f">
          <label>City</label>
          <input value={draft.city} onChange={(e) => setField("city", e.target.value)} placeholder="City" />
        </div>

        <div className="f">
          <label>State</label>
          <input value={draft.state} onChange={(e) => setField("state", e.target.value)} placeholder="State" />
        </div>

        <div className="f">
          <label>Country</label>
          <input value={draft.country} onChange={(e) => setField("country", e.target.value)} placeholder="Country" />
        </div>

        <div className="f">
          <label>Website</label>
          <input value={draft.website} onChange={(e) => setField("website", e.target.value)} placeholder="Optional" />
        </div>

        <div className="f full">
          <label>Created Date (auto)</label>
          <input value={createdLabel} readOnly />
        </div>
      </div>

      {state.ui.toast ? <div id="toast" className="toast">{state.ui.toast}</div> : null}
    </Modal>
  );
}

/**
 * ---------------------------
 * Profile Modal (enhanced)
 * ---------------------------
 */
function ProfileModal() {
  const { state, dispatch } = useApp();
  const open = state.ui.profileOpen;
  const firmName = state.firm?.firm_name || state.firm?.name || "";

  const [draft, setDraft] = React.useState(() => ({
    email: state.profile?.email || "",
    first_name: state.profile?.first_name || "",
    last_name: state.profile?.last_name || "",
    phone: state.profile?.phone || "",
    address: state.profile?.address || "",
    role: state.profile?.role || "owner_admin",
  }));

  useEffect(() => {
    if (!open) return;
    setDraft({
      email: state.profile?.email || "",
      first_name: state.profile?.first_name || "",
      last_name: state.profile?.last_name || "",
      phone: state.profile?.phone || "",
      address: state.profile?.address || "",
      role: state.profile?.role || "owner_admin",
    });
  }, [open, state.profile]);

  function setField(key, value) {
    setDraft((p) => ({ ...p, [key]: value }));
  }

  async function onSave() {
    try {
      dispatch({ type: "UI/TOAST", kind: "info", message: "Saving profile..." });

      const payload = JSON.stringify({ ...draft });
      const data = await apiFetch(CONFIG.endpoints.profileSave, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: payload,
      });

      const profile = data?.profile || draft;
      dispatch({ type: "PROFILE/SET", profile });
      dispatch({ type: "UI/TOAST", kind: "success", message: "Profile saved ✅" });

      setTimeout(() => {
        dispatch({ type: "UI/CLOSE_PROFILE" });
        dispatch({ type: "UI/TOAST", message: "" });
      }, 600);
    } catch (e) {
      dispatch({ type: "UI/TOAST", kind: "error", message: e.message || "Error saving ❌" });
    }
  }

  return (
    <Modal
      open={open}
      title="Profile"
      subtitle="Update your basic details"
      onClose={() => dispatch({ type: "UI/CLOSE_PROFILE" })}
      footer={
        <>
          <button className="btn btn-ghost" type="button" onClick={() => dispatch({ type: "UI/CLOSE_PROFILE" })}>
            Cancel
          </button>
          <button className="btn btn-save" type="button" onClick={onSave}>
            Save
          </button>
        </>
      }
    >
      <div className="modal-grid">
        <div className="f">
          <label>Username</label>
          <input value={state.profile?.username || ""} readOnly />
        </div>

        <div className="f">
          <label>Firm Name (auto-filled)</label>
          <input value={firmName} readOnly placeholder="Create/select a firm first" />
        </div>

        <div className="f">
          <label>Role *</label>
          <select value={draft.role} onChange={(e) => setField("role", e.target.value)}>
            {ROLE_OPTIONS.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </div>

        <div className="f">
          <label>Email</label>
          <input value={draft.email} onChange={(e) => setField("email", e.target.value)} placeholder="admin@inventtech.com" />
        </div>

        <div className="f">
          <label>First name</label>
          <input value={draft.first_name} onChange={(e) => setField("first_name", e.target.value)} placeholder="Your name" />
        </div>

        <div className="f">
          <label>Last name</label>
          <input value={draft.last_name} onChange={(e) => setField("last_name", e.target.value)} placeholder="Surname" />
        </div>

        <div className="f">
          <label>Mobile</label>
          <input value={draft.phone} onChange={(e) => setField("phone", e.target.value)} placeholder="98XXXXXXXX" />
        </div>

        <div className="f full">
          <label>Address</label>
          <textarea value={draft.address} onChange={(e) => setField("address", e.target.value)} rows={3} placeholder="Optional" />
        </div>
      </div>

      {state.ui.toast ? <div id="toast" className="toast">{state.ui.toast}</div> : null}
    </Modal>
  );
}

/**
 * ---------------------------
 * Header Buttons (Firm + Profile)
 * ---------------------------
 * Matches your existing iconbtn UI pattern.
 */
function HeaderActions() {
  const { dispatch } = useApp();
  const firmBtnId = useId();
  const profileBtnId = useId();

  return (
    <>
      {/* Firm button */}
      <button
        className="iconbtn"
        id={firmBtnId}
        type="button"
        title="Firm"
        onClick={() => dispatch({ type: "UI/OPEN_FIRM" })}
      >
        {/* simple building icon */}
        <svg className="ico" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M3 21V3h12v18H3zm14 0v-8h4v8h-4zM6 7h6M6 11h6M6 15h6" />
        </svg>
      </button>

      {/* Profile button */}
      <button
        className="iconbtn btnProfile"
        id={profileBtnId}
        type="button"
        title="Profile"
        onClick={() => dispatch({ type: "UI/OPEN_PROFILE" })}
      >
        <svg className="ico" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4zm-8 9a8 8 0 0 1 16 0" />
        </svg>
      </button>

      {/* Keep your existing notification/settings buttons in Django template if you want,
          or convert them later to React similarly. */}

      <FirmModal />
      <ProfileModal />
    </>
  );
}

/**
 * ---------------------------
 * Mount
 * ---------------------------
 */
function Mount() {
  return (
    <AppProvider>
      <HeaderActions />
    </AppProvider>
  );
}

const mountEl = document.getElementById("inventtech-header-actions");
if (mountEl) {
  createRoot(mountEl).render(<Mount />);
}
