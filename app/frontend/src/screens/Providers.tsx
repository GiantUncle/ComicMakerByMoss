import { useEffect, useState } from "react";
import { api, type ModelGroup, type ProviderInfo, type ProvidersPayload } from "../api";

/**
 * Four provider slots — Google, OpenCode, NVIDIA, Custom. Each holds a base URL
 * and a key, and can fetch its own model list. The last model used per provider
 * is remembered, and a model can be starred into the favourites block.
 */
export default function Providers() {
  const [data, setData] = useState<ProvidersPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const load = () => api.providers().then(setData).catch((e) => setError(String(e)));
  useEffect(() => {
    load();
  }, []);

  const groupOf = (id: string): ModelGroup | undefined =>
    data?.groups.find((g) => g.provider === id);

  return (
    <div className="stack" style={{ maxWidth: 820 }}>
      <div className="between">
        <h1 style={{ margin: 0, fontSize: "var(--text-xl)" }}>프로바이더</h1>
        <button className="btn" onClick={() => api.refreshModels().then(setData)}>
          ↻ 모두 새로 고침
        </button>
      </div>
      <p className="muted" style={{ margin: 0 }}>
        OpenAI 호환 엔드포인트면 무엇이든 됩니다. 키는 서버에만 저장되고 다시 조회되지 않습니다.
        상단의 <strong>모델</strong> 메뉴에서 고르거나, 여기서 프로바이더별로 고를 수 있습니다.
      </p>

      {note && <div className="card chip--ok">✓ {note}</div>}
      {error && (
        <div className="card chip--bad">
          오류: <span className="mono">{error}</span>
        </div>
      )}

      {data?.providers.map((p) => (
        <ProviderCard
          key={p.id}
          p={p}
          group={groupOf(p.id)}
          active={data.active}
          onSaved={(m) => {
            setNote(m);
            load();
          }}
        />
      ))}
    </div>
  );
}

function ProviderCard({
  p,
  group,
  active,
  onSaved,
}: {
  p: ProviderInfo;
  group?: ModelGroup;
  active: { provider?: string; model?: string };
  onSaved: (msg: string) => void;
}) {
  const [baseUrl, setBaseUrl] = useState(p.base_url);
  const [apiKey, setApiKey] = useState("");
  const [jsonMode, setJsonMode] = useState(p.supports_json_mode ?? true);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setBaseUrl(p.base_url);
    setJsonMode(p.supports_json_mode ?? true);
  }, [p.base_url, p.supports_json_mode]);

  async function save() {
    setBusy(true);
    setErr(null);
    setMsg(null);
    try {
      await api.saveProvider({
        id: p.id,
        label: p.label,
        base_url: baseUrl,
        api_key: apiKey || undefined,
        supports_json_mode: jsonMode,
      });
      setApiKey("");
      onSaved(`${p.label ?? p.id} 저장`);
      setMsg("저장했습니다.");
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function refresh() {
    setBusy(true);
    setErr(null);
    setMsg(null);
    try {
      const r = await api.refreshModels(p.id);
      setMsg(`모델 ${r.groups.find((g) => g.provider === p.id)?.models.length ?? 0}개`);
      onSaved(`${p.label ?? p.id} 모델 목록 갱신`);
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function test() {
    setBusy(true);
    setErr(null);
    setMsg(null);
    try {
      const r = await api.testProvider({ provider_id: p.id, model: group?.selected ?? undefined });
      if (r.ok) setMsg(`연결됨 — ${r.reply}`);
      else setErr(r.error ?? "연결 실패");
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  const models = group?.models ?? [];
  const favs = group?.favorites ?? [];

  return (
    <div className="card stack">
      <div className="between">
        <div className="row">
          <strong>{p.label ?? p.id}</strong>
          <span className="mono muted" style={{ fontSize: "var(--text-sm)" }}>
            {p.id}
          </span>
          {p.api_key_set && <span className="chip chip--ok">키 설정됨</span>}
          {active.provider === p.id && active.model && <span className="chip">사용 중</span>}
        </div>
        <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
          {group?.fetched ? `갱신 ${group.fetched.replace("T", " ")}` : "목록 없음"}
        </span>
      </div>

      {msg && <div className="chip chip--ok">{msg}</div>}
      {err && (
        <div className="chip--bad" style={{ fontSize: "var(--text-sm)" }}>
          {err}
        </div>
      )}

      <div className="field" style={{ marginBottom: 0 }}>
        <label>Base URL</label>
        <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="https://…/v1" />
      </div>
      <div className="field" style={{ marginBottom: 0 }}>
        <label>
          API 키 {p.api_key_set && <span className="muted">(설정됨 — 바꾸려면 입력)</span>}
        </label>
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder={p.api_key_set ? "••••••••" : "key"}
        />
      </div>
      <label className="row">
        <input type="checkbox" checked={jsonMode} onChange={(e) => setJsonMode(e.target.checked)} />
        JSON 모드(response_format) 지원
      </label>

      <div className="row" style={{ flexWrap: "wrap" }}>
        <button className="btn btn--primary" onClick={save} disabled={busy || !baseUrl}>
          저장
        </button>
        <button className="btn" onClick={refresh} disabled={busy || !baseUrl}>
          ↻ 모델 불러오기
        </button>
        <button className="btn" onClick={test} disabled={busy || !p.api_key_set}>
          연결 테스트
        </button>
      </div>

      {models.length > 0 && (
        <div style={{ borderTop: "1px solid var(--border-soft)", paddingTop: "var(--s-3)" }}>
          <div className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "var(--s-2)" }}>
            모델 {models.length}개 — 별을 누르면 즐겨찾기, 이름을 누르면 이 프로바이더의 마지막 선택으로 저장
          </div>
          <div style={{ maxHeight: 260, overflow: "auto" }}>
            {models.map((m) => {
              const fav = favs.includes(m);
              const chosen = group?.selected === m;
              return (
                <div
                  key={m}
                  className="row"
                  style={{
                    gap: "var(--s-2)",
                    padding: "var(--s-1) var(--s-2)",
                    borderBottom: "1px solid var(--border-soft)",
                    fontSize: "var(--text-sm)",
                  }}
                >
                  <span
                    role="button"
                    aria-label={fav ? "즐겨찾기 해제" : "즐겨찾기"}
                    style={{ width: 16, cursor: "pointer", color: fav ? "var(--warning)" : "var(--fg-muted)" }}
                    onClick={() => api.favoriteModel(p.id, m, !fav).then(onSaved.bind(null, `${m} 즐겨찾기`))}
                  >
                    {fav ? "★" : "☆"}
                  </span>
                  <span
                    role="button"
                    tabIndex={0}
                    style={{ flex: 1, cursor: "pointer" }}
                    onClick={() => api.selectModel(p.id, m).then(onSaved.bind(null, `${m} 선택`))}
                    onKeyDown={(e) => e.key === "Enter" && api.selectModel(p.id, m).then(onSaved.bind(null, `${m} 선택`))}
                  >
                    {m}
                  </span>
                  {chosen && <span className="chip chip--ok">선택</span>}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
