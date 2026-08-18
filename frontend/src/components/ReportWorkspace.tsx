import { FormEvent, useEffect, useRef, useState } from 'react';
import {
  CheckCircle2,
  ClipboardPaste,
  FileCheck2,
  FileText,
  Hash,
  Loader2,
  LogOut,
  Mail,
  Mic,
  MicOff,
  RotateCcw,
  Search,
  Sparkles,
  Stethoscope,
  UserRound,
  UsersRound,
} from 'lucide-react';

import { apiRequest } from '../lib/api';
import type { SpeechRecognitionLike } from '../lib/speech';
import type {
  AppConfig,
  Patient,
  PublishResult,
  ReportForm,
  ReportModelId,
  ReportModelOption,
  SheetSelection,
  User,
} from '../lib/types';
import { ReportDraftEditor } from './ReportDraftEditor';
import { UserManagementPanel } from './UserManagementPanel';

function createInitialForm(): ReportForm {
  return {
    recordData: '',
    ciPaciente: '',
    nombrePaciente: '',
    doctor_gender: 'Dra.',
    doctor: '',
    fecha: new Date().toLocaleDateString('en-CA'),
    measures: '0.5',
    texto: '',
    driveUrl: '',
    recipientEmail: '',
    createGmailDraft: false,
    approved: false,
  };
}

interface ReportWorkspaceProps {
  user: User;
  onLogout: () => void;
}

export function ReportWorkspace({ user, onLogout }: ReportWorkspaceProps) {
  const [form, setForm] = useState<ReportForm>(createInitialForm);
  const [query, setQuery] = useState('');
  const [rowNumber, setRowNumber] = useState('');
  const [patients, setPatients] = useState<Patient[]>([]);
  const [sheetNames, setSheetNames] = useState<string[]>([]);
  const [selectedSheet, setSelectedSheet] = useState('');
  const [loadingSheets, setLoadingSheets] = useState(true);
  const [transcript, setTranscript] = useState('');
  const [generatedDraft, setGeneratedDraft] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [recording, setRecording] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(true);
  const [busyAction, setBusyAction] = useState<'search' | 'row' | 'generate' | 'publish' | null>(null);
  const [error, setError] = useState('');
  const [result, setResult] = useState<PublishResult | null>(null);
  const [gmailDraftEnabled, setGmailDraftEnabled] = useState(false);
  const [reportModels, setReportModels] = useState<ReportModelOption[]>([]);
  const [selectedReportModel, setSelectedReportModel] = useState<ReportModelId>(
    'gemini-3.5-flash-lite',
  );
  const [showUserManagement, setShowUserManagement] = useState(false);

  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const recordingRef = useRef(false);
  const patientSearchRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    apiRequest<AppConfig>('/config')
      .then((config) => {
        const storageKey = `imagen-report:report-model:${user.id}`;
        const legacyStorageKey = `imagen-report:gemini-model:${user.id}`;
        const rememberedModel = window.localStorage.getItem(storageKey)
          ?? window.localStorage.getItem(legacyStorageKey);
        const rememberedOption = config.report_models.find(
          (option) => option.id === rememberedModel,
        );
        setGmailDraftEnabled(config.gmail_draft_enabled);
        setReportModels(config.report_models);
        setSelectedReportModel(rememberedOption?.id ?? config.report_default_model);
      })
      .catch(() => setGmailDraftEnabled(false));
  }, [user.id]);

  useEffect(() => {
    apiRequest<SheetSelection>('/patients/sheets')
      .then((selection) => {
        const storageKey = `imagen-report:selected-sheet:${user.id}`;
        const rememberedSheet = window.localStorage.getItem(storageKey);
        const initialSheet = rememberedSheet && selection.sheets.includes(rememberedSheet)
          ? rememberedSheet
          : selection.default_sheet;
        setSheetNames(selection.sheets);
        setSelectedSheet(initialSheet);
      })
      .catch((requestError: unknown) => {
        setError(
          requestError instanceof Error
            ? requestError.message
            : 'No fue posible consultar las hojas disponibles.',
        );
      })
      .finally(() => setLoadingSheets(false));
  }, [user.id]);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSpeechSupported(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'es-ES';
    recognition.onresult = (event) => {
      let finalText = '';
      let interimText = '';
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const resultItem = event.results[index];
        if (resultItem.isFinal) finalText += resultItem[0].transcript;
        else interimText += resultItem[0].transcript;
      }
      if (finalText) {
        setTranscript((current) => `${current}${current.trim() ? ' ' : ''}${finalText.trim()}`);
      }
      setInterimTranscript(interimText);
    };
    recognition.onerror = (event) => {
      if (event.error !== 'no-speech') {
        setError(`El reconocimiento de voz informó: ${event.error}.`);
      }
      if (['not-allowed', 'service-not-allowed', 'language-not-supported'].includes(event.error)) {
        recordingRef.current = false;
        setRecording(false);
      }
    };
    recognition.onend = () => {
      if (recordingRef.current) {
        try {
          recognition.start();
        } catch {
          recordingRef.current = false;
          setRecording(false);
        }
      }
    };
    recognitionRef.current = recognition;
    return () => {
      recordingRef.current = false;
      recognition.onend = null;
      recognition.abort();
    };
  }, []);

  function updateField<K extends keyof ReportForm>(field: K, value: ReportForm[K]) {
    setForm((current) => ({
      ...current,
      [field]: value,
      ...(field === 'texto' ? { approved: false } : {}),
    }));
    setResult(null);
  }

  async function searchPatients() {
    if (query.trim().length < 2) return;
    setBusyAction('search');
    setError('');
    try {
      const sheetParameter = selectedSheet
        ? `&sheet=${encodeURIComponent(selectedSheet)}`
        : '';
      setPatients(
        await apiRequest<Patient[]>(
          `/patients?query=${encodeURIComponent(query.trim())}${sheetParameter}`,
        ),
      );
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'No fue posible consultar la planilla.');
    } finally {
      setBusyAction(null);
    }
  }

  async function loadPatientByRow() {
    const parsedRow = Number(rowNumber);
    if (!Number.isInteger(parsedRow) || parsedRow < 1) return;
    setBusyAction('row');
    setError('');
    try {
      const sheetParameter = selectedSheet
        ? `?sheet=${encodeURIComponent(selectedSheet)}`
        : '';
      const patient = await apiRequest<Patient>(
        `/patients/row/${parsedRow}${sheetParameter}`,
      );
      selectPatient(patient);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'No fue posible cargar la fila indicada.',
      );
    } finally {
      setBusyAction(null);
    }
  }

  function selectPatient(patient: Patient) {
    setForm((current) => ({
      ...current,
      nombrePaciente: patient.nombrePaciente,
      ciPaciente: patient.ciPaciente,
      doctor: patient.doctor,
      recipientEmail: patient.recipientEmail || '',
      driveUrl: patient.driveUrl || '',
    }));
    setPatients([]);
    setQuery('');
    setRowNumber('');
  }

  function parseRecordData(value: string) {
    updateField('recordData', value);
    const [nombrePaciente, doctor, ciPaciente] = value.split('\t').map((item) => item.trim());
    if (nombrePaciente && doctor && ciPaciente) {
      setForm((current) => ({ ...current, recordData: value, nombrePaciente, doctor, ciPaciente }));
    }
  }

  function toggleRecording() {
    setError('');
    if (recording) {
      recordingRef.current = false;
      setRecording(false);
      setInterimTranscript('');
      recognitionRef.current?.stop();
      return;
    }
    try {
      recognitionRef.current?.start();
      recordingRef.current = true;
      setRecording(true);
    } catch {
      setError('No fue posible iniciar el micrófono.');
    }
  }

  async function generateDraft() {
    if (!transcript.trim()) return;
    if (recording) toggleRecording();
    setBusyAction('generate');
    setError('');
    try {
      const response = await apiRequest<{ report: string }>('/reports/generate', {
        method: 'POST',
        body: JSON.stringify({ transcript, model: selectedReportModel }),
      });
      setGeneratedDraft(response.report);
      setForm((current) => ({ ...current, texto: response.report, approved: false }));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'No fue posible generar el borrador.');
    } finally {
      setBusyAction(null);
    }
  }

  async function publishReport(event: FormEvent) {
    event.preventDefault();
    setBusyAction('publish');
    setError('');
    setResult(null);
    const { recordData: _recordData, recipientEmail, ...payload } = form;
    void _recordData;
    try {
      const publishResult = await apiRequest<PublishResult>('/reports/publish', {
        method: 'POST',
        body: JSON.stringify({
          ...payload,
          recipientEmail: recipientEmail.trim() || null,
        }),
      });
      setResult(publishResult);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'No fue posible crear el documento.');
    } finally {
      setBusyAction(null);
    }
  }

  async function logout() {
    await apiRequest<void>('/auth/logout', { method: 'POST' }).catch(() => undefined);
    onLogout();
  }

  function startNewReport() {
    recordingRef.current = false;
    recognitionRef.current?.abort();
    setRecording(false);
    setForm(createInitialForm());
    setQuery('');
    setRowNumber('');
    setPatients([]);
    setTranscript('');
    setGeneratedDraft('');
    setInterimTranscript('');
    setBusyAction(null);
    setError('');
    setResult(null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
    window.requestAnimationFrame(() => patientSearchRef.current?.focus());
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-row">
          <div className="brand-mark small"><Stethoscope size={19} /></div>
          <div>
            <strong>Imagen Report</strong>
            <span>Informes radiológicos</span>
          </div>
        </div>
        <div className="user-menu">
          {user.is_admin && (
            <button type="button" className="admin-nav-button" onClick={() => setShowUserManagement(true)}>
              <UsersRound size={17} /> Usuarios
            </button>
          )}
          <div>
            <strong>{user.username}</strong>
            <span>{user.email}</span>
          </div>
          <button type="button" className="icon-button" onClick={logout} title="Cerrar sesión">
            <LogOut size={18} />
          </button>
        </div>
      </header>

      {showUserManagement && (
        <UserManagementPanel
          currentUser={user}
          onClose={() => setShowUserManagement(false)}
          onCurrentUserPasswordReset={onLogout}
        />
      )}

      <main className="workspace">
        <section className="page-heading">
          <div>
            <p className="eyebrow">Nuevo informe</p>
            <h1>Dictado y generación de documento</h1>
            <p className="muted">Complete el flujo y apruebe el texto antes de crear el PDF.</p>
          </div>
          <ol className="steps" aria-label="Etapas del informe">
            <li className={form.nombrePaciente ? 'done' : 'active'}><span>1</span> Paciente</li>
            <li className={transcript ? 'done' : ''}><span>2</span> Dictado</li>
            <li className={form.approved ? 'done' : ''}><span>3</span> Revisión</li>
            <li className={result ? 'done' : ''}><span>4</span> Documento</li>
          </ol>
        </section>

        {error && <div className="notice error global-notice" role="alert">{error}</div>}

        <form onSubmit={publishReport} className="report-grid">
          <section className="card span-two">
            <div className="card-header">
              <div><UserRound size={19} /><div><h2>Paciente y solicitante</h2><p>Datos de la Google Sheet o ingreso asistido.</p></div></div>
            </div>

            <div className="search-row sheet-search-row">
              <label className="sheet-selector">
                Hoja de trabajo
                <select
                  value={selectedSheet}
                  onChange={(event) => {
                    const sheetName = event.target.value;
                    setSelectedSheet(sheetName);
                    window.localStorage.setItem(
                      `imagen-report:selected-sheet:${user.id}`,
                      sheetName,
                    );
                    setPatients([]);
                  }}
                  disabled={loadingSheets || sheetNames.length === 0}
                >
                  {loadingSheets && <option value="">Cargando hojas…</option>}
                  {!loadingSheets && sheetNames.length === 0 && (
                    <option value="">Hoja configurada por defecto</option>
                  )}
                  {sheetNames.map((sheetName) => (
                    <option key={sheetName} value={sheetName}>{sheetName}</option>
                  ))}
                </select>
                <small>Seleccione el mes o período que desea consultar.</small>
              </label>
              <label className="grow">
                Buscar por nombre, cédula o médico
                <div className="input-with-icon">
                  <Search size={17} />
                  <input
                    ref={patientSearchRef}
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key !== 'Enter' || event.nativeEvent.isComposing) return;
                      event.preventDefault();
                      if (busyAction === 'search' || query.trim().length < 2) return;
                      void searchPatients();
                    }}
                    placeholder="Escriba al menos dos caracteres"
                  />
                </div>
              </label>
              <button className="secondary-button sheet-search-button" type="button" onClick={searchPatients} disabled={busyAction === 'search' || query.trim().length < 2}>
                {busyAction === 'search' ? <Loader2 className="spin" size={17} /> : <Search size={17} />} Consultar
              </button>
            </div>

            <div className="row-lookup-row">
              <div className="row-lookup-copy">
                <strong>Cargar una fila exacta</strong>
                <small>Úselo cuando un paciente figure más de una vez en la hoja seleccionada.</small>
              </div>
              <label>
                Número de fila
                <div className="input-with-icon">
                  <Hash size={17} />
                  <input
                    type="number"
                    min="1"
                    step="1"
                    inputMode="numeric"
                    value={rowNumber}
                    onChange={(event) => setRowNumber(event.target.value)}
                    placeholder="Ej. 42"
                  />
                </div>
              </label>
              <button
                className="secondary-button align-end"
                type="button"
                onClick={loadPatientByRow}
                disabled={
                  busyAction === 'row'
                  || !Number.isInteger(Number(rowNumber))
                  || Number(rowNumber) < 1
                }
              >
                {busyAction === 'row' ? <Loader2 className="spin" size={17} /> : <Hash size={17} />}
                Cargar fila
              </button>
            </div>

            {patients.length > 0 && (
              <div className="patient-results">
                {patients.map((patient) => (
                  <button type="button" key={patient.row_number} onClick={() => selectPatient(patient)}>
                    <strong>{patient.nombrePaciente}</strong>
                    <span>Fila {patient.row_number} · CI {patient.ciPaciente} · {patient.doctor || 'Sin médico'}</span>
                  </button>
                ))}
              </div>
            )}

            <label>
              <span className="label-with-icon"><ClipboardPaste size={15} /> Datos pegados desde la planilla</span>
              <input value={form.recordData} onChange={(event) => parseRecordData(event.target.value)} placeholder="Nombre[TAB]Doctor[TAB]Cédula" />
            </label>

            <div className="field-grid three">
              <label>Nombre del paciente<input value={form.nombrePaciente} onChange={(event) => updateField('nombrePaciente', event.target.value)} required /></label>
              <label>Cédula de identidad<input value={form.ciPaciente} onChange={(event) => updateField('ciPaciente', event.target.value)} required /></label>
              <label>Fecha<input type="date" value={form.fecha} onChange={(event) => updateField('fecha', event.target.value)} required /></label>
              <label>
                Tratamiento
                <select value={form.doctor_gender} onChange={(event) => updateField('doctor_gender', event.target.value as 'Dr.' | 'Dra.')}>
                  <option value="Dr.">Dr.</option><option value="Dra.">Dra.</option>
                </select>
              </label>
              <label className="span-two-fields">Médico solicitante<input value={form.doctor} onChange={(event) => updateField('doctor', event.target.value)} required /></label>
              <label>Medidas (mm)<input value={form.measures} onChange={(event) => updateField('measures', event.target.value)} required /></label>
              <label className="span-two-fields">Enlace Google Drive<input type="url" value={form.driveUrl} onChange={(event) => updateField('driveUrl', event.target.value)} placeholder="https://drive.google.com/..." required /></label>
            </div>
          </section>

          <section className="card">
            <div className="card-header">
              <div><Mic size={19} /><div><h2>Dictado original</h2><p>La transcripción puede corregirse antes de utilizar IA.</p></div></div>
              <span className={`status-pill ${recording ? 'recording' : ''}`}>{recording ? 'En vivo' : 'Listo'}</span>
            </div>
            <textarea className="editor transcript" value={transcript} onChange={(event) => setTranscript(event.target.value)} placeholder="El dictado aparecerá aquí..." />
            {interimTranscript && <p className="interim-text">{interimTranscript}</p>}
            {!speechSupported && <div className="notice warning">El navegador no ofrece reconocimiento de voz. Puede escribir o pegar la transcripción.</div>}
            <div className="button-row">
              <button type="button" className={recording ? 'danger-button' : 'primary-button'} onClick={toggleRecording} disabled={!speechSupported}>
                {recording ? <MicOff size={18} /> : <Mic size={18} />} {recording ? 'Detener' : 'Comenzar dictado'}
              </button>
              <button type="button" className="secondary-button" onClick={() => { setTranscript(''); setInterimTranscript(''); }} disabled={!transcript && !interimTranscript}>Descartar</button>
            </div>
          </section>

          <section className="card">
            <div className="card-header">
              <div><Sparkles size={19} /><div><h2>Borrador técnico</h2><p>Generado por IA; requiere revisión profesional.</p></div></div>
            </div>
            <label className="report-model-selector">
              Modelo para generar el borrador
              <select
                value={selectedReportModel}
                onChange={(event) => {
                  const model = event.target.value as ReportModelId;
                  setSelectedReportModel(model);
                  window.localStorage.setItem(
                    `imagen-report:report-model:${user.id}`,
                    model,
                  );
                }}
                disabled={reportModels.length === 0 || busyAction === 'generate'}
              >
                {reportModels.map((model) => (
                  <option key={model.id} value={model.id}>{model.label}</option>
                ))}
              </select>
              <small>
                {reportModels.find((model) => model.id === selectedReportModel)?.description
                  ?? 'Se utilizará en la próxima generación.'}
              </small>
            </label>
            <ReportDraftEditor
              value={form.texto}
              generatedDraft={generatedDraft}
              approved={form.approved}
              canGenerate={Boolean(transcript.trim())}
              isGenerating={busyAction === 'generate'}
              onChange={(value) => updateField('texto', value)}
              onGenerate={generateDraft}
            />
            <label className="approval-box">
              <input type="checkbox" checked={form.approved} onChange={(event) => updateField('approved', event.target.checked)} disabled={!form.texto.trim()} />
              <span><strong>Informe revisado y aprobado</strong><small>Confirmo que el texto fue verificado por un profesional.</small></span>
            </label>
          </section>

          <section className="card span-two">
            <div className="card-header">
              <div><FileCheck2 size={19} /><div><h2>Documento final</h2><p>Se creará desde la plantilla institucional y se guardará en Drive.</p></div></div>
            </div>
            {gmailDraftEnabled ? (
              <>
                <label className="gmail-option">
                  <input type="checkbox" checked={form.createGmailDraft} onChange={(event) => updateField('createGmailDraft', event.target.checked)} />
                  <Mail size={18} />
                  <span><strong>Crear borrador en Gmail</strong><small>Opcional para este informe. El correo no se enviará automáticamente.</small></span>
                </label>
                {form.createGmailDraft && (
                  <label className="recipient-field">Correo del destinatario<input type="email" value={form.recipientEmail} onChange={(event) => updateField('recipientEmail', event.target.value)} placeholder="medico@gmail.com" required /></label>
                )}
              </>
            ) : (
              <div className="notice warning">
                <Mail size={18} />
                La creación de borradores de Gmail está desactivada en esta instalación.
              </div>
            )}

            <button type="submit" className="publish-button" disabled={!form.approved || busyAction === 'publish'}>
              {busyAction === 'publish' ? <Loader2 className="spin" size={19} /> : <FileText size={19} />}
              Crear Google Doc y PDF{form.createGmailDraft ? ' + borrador de correo' : ''}
            </button>

            {result && (
              <div className="result-card">
                <CheckCircle2 size={24} />
                <div><strong>Informe generado correctamente</strong><p>Los archivos quedaron guardados en Google Drive.</p></div>
                <div className="result-links">
                  <a href={result.document_url} target="_blank" rel="noreferrer">Abrir Google Doc</a>
                  <a href={result.pdf_url} target="_blank" rel="noreferrer">Abrir PDF</a>
                  {result.gmail_draft_id && <span>Borrador de Gmail creado</span>}
                  <button type="button" className="new-report-button" onClick={startNewReport}>
                    <RotateCcw size={14} /> Nuevo informe
                  </button>
                </div>
              </div>
            )}
          </section>
        </form>
      </main>
    </div>
  );
}
