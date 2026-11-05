/* GoldenTable · interfaz web. Consume la API REST (JWT) a través del proxy /api de nginx. */
"use strict";

const API = "/api";
const CLAVE_SESION = "gt_sesion";
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const cop = (n) => "$" + Math.round(Number(n) || 0).toLocaleString("es-CO");
const fechaIso = (d) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
const hoy = () => fechaIso(new Date());
const manana = () => fechaIso(new Date(Date.now() + 864e5));
const HORAS = ["18:00", "19:00", "20:00", "21:00", "22:00"];

/* ---------------- sesión (JWT) ---------------- */
let sesion = null;
function leerSesion() {
  try { return JSON.parse(localStorage.getItem(CLAVE_SESION)); } catch (e) { return null; }
}
function guardarSesion(s) {
  sesion = s;
  try { localStorage.setItem(CLAVE_SESION, JSON.stringify(s)); } catch (e) { /* sin almacenamiento */ }
}
function cerrarSesion(mensaje) {
  sesion = null;
  try { localStorage.removeItem(CLAVE_SESION); } catch (e) { /* ignorar */ } // fin de sesión = borrar el token
  mostrarLogin();
  if (mensaje) toast(mensaje, "err");
}

/* ---------------- utilidades de UI ---------------- */
let temporizador;
function toast(msg, tipo) {
  const t = $("toast");
  t.textContent = msg;
  t.className = "show " + (tipo || "");
  clearTimeout(temporizador);
  temporizador = setTimeout(() => { t.className = ""; }, 4500);
}

async function api(metodo, ruta, cuerpo, opciones = {}) {
  const { auth = true, blob = false } = opciones;
  const cabeceras = {};
  if (cuerpo !== undefined) cabeceras["Content-Type"] = "application/json";
  if (auth && sesion) cabeceras["Authorization"] = "Bearer " + sesion.token; // token en cada petición protegida
  const r = await fetch(API + ruta, { method: metodo, headers: cabeceras, body: cuerpo !== undefined ? JSON.stringify(cuerpo) : undefined });
  if (r.status === 401 && auth) {
    cerrarSesion("Tu sesión expiró o no es válida. Inicia sesión de nuevo.");
    throw new Error("Sesión expirada");
  }
  if (!r.ok) {
    let detalle = "Error " + r.status;
    try {
      const d = (await r.json()).detail;
      detalle = Array.isArray(d) ? d.map((x) => x.msg).join(" · ") : d || detalle;
    } catch (e) { /* sin cuerpo */ }
    throw new Error(detalle);
  }
  return blob ? r.blob() : r.json();
}

async function ejecutar(fn, boton) {
  if (boton) boton.disabled = true;
  try { await fn(); } catch (e) { if (e.message !== "Sesión expirada") toast(e.message, "err"); } finally { if (boton) boton.disabled = false; }
}
function alClic(id, fn) {
  const el = $(id);
  if (el) el.onclick = () => ejecutar(fn, el);
}
const tabla = (cabeceras, filas) =>
  `<div class="tabla-wrap"><table><thead><tr>${cabeceras.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>${filas.join("")}</tbody></table></div>`;
const vacio = (texto) => `<div class="vacio">${esc(texto)}</div>`;
const optsHoras = () => HORAS.map((h) => `<option>${h}</option>`).join("");
const estadoChip = (e) => (e === "en_curso" ? '<span class="chip ok">En curso</span>' : '<span class="chip warn">Confirmada</span>');

/* ---------------- secciones ---------------- */
const SECCIONES = {};
const NAV = {
  cliente: [["reservas", "Reservas"], ["fidelidad", "Fidelidad"], ["billetera", "Billetera"], ["avisos", "Notificaciones"], ["responsable", "Juego responsable"]],
  anfitrion: [["agenda", "Reservas del día"], ["avisos", "Notificaciones"]],
  cajero: [["caja", "Caja"]],
  gerente: [["agenda", "Reservas del día"], ["caja", "Caja"], ["reportes", "Reportes"], ["avisos", "Notificaciones"]],
};
const ROLES = { cliente: "Cliente", anfitrion: "Anfitrión", cajero: "Cajero", gerente: "Gerente" };

/* ----- Cliente: reservas (HU-01, HU-02) ----- */
SECCIONES.reservas = async (el) => {
  el.innerHTML = `
  <div class="grid">
    <div class="card ancha">
      <h2>Reserva tu mesa</h2><p class="sub">Elige fecha y hora, y reserva con un clic.</p>
      <div class="row">
        <div><label for="r-fecha">Fecha</label><input type="date" id="r-fecha" min="${hoy()}" value="${manana()}"></div>
        <div><label for="r-hora">Hora</label><select id="r-hora">${optsHoras()}</select></div>
        <div class="acciones"><button class="btn" id="r-buscar" type="button">Ver mesas</button></div>
      </div>
      <div id="r-mesas"></div><div id="r-codigo"></div>
    </div>
    <div class="card ancha"><h2>Mis reservas</h2><p class="sub">Presenta tu código al anfitrión para hacer check-in.</p><div id="r-mias"></div></div>
  </div>`;

  const verMesas = async () => {
    const f = $("r-fecha").value, h = $("r-hora").value;
    if (!f) { toast("Elige una fecha", "err"); return; }
    const mesas = await api("GET", `/disponibilidad?fecha=${f}&hora=${encodeURIComponent(h)}`);
    $("r-mesas").innerHTML = mesas.length
      ? `<div class="tables">${mesas.map((m) => `<div class="mesa"><b>Mesa ${m.id}</b><span>${m.capacidad} personas · ${esc(m.horario)}</span><button class="btn sm" data-mesa="${m.id}" type="button">Reservar</button></div>`).join("")}</div>`
      : vacio("No hay mesas libres a esa hora. Prueba con otra franja.");
    $("r-mesas").querySelectorAll("button[data-mesa]").forEach((b) => { b.onclick = () => ejecutar(() => reservar(+b.dataset.mesa), b); });
  };
  const misReservas = async () => {
    const rs = await api("GET", "/reservas/mias");
    $("r-mias").innerHTML = rs.length
      ? tabla(["Código", "Fecha", "Hora", "Mesa", "Estado"], rs.map((r) => `<tr><td><b>${esc(r.codigo_confirmacion)}</b></td><td>${esc(r.fecha)}</td><td>${esc(r.hora)}</td><td>${r.mesa_id}</td><td>${estadoChip(r.estado)}</td></tr>`))
      : vacio("Aún no tienes reservas.");
  };
  const reservar = async (mesaId) => {
    const r = await api("POST", "/reservas", { mesa_id: mesaId, fecha: $("r-fecha").value, hora: $("r-hora").value });
    $("r-codigo").innerHTML = `<div class="codigo">${esc(r.codigo_confirmacion)}</div><p class="sub" style="text-align:center;margin-top:8px">¡Reserva confirmada! Guarda este código para tu check-in.</p>`;
    toast("Reserva confirmada · mesa " + mesaId, "good");
    await verMesas(); await misReservas();
  };
  alClic("r-buscar", verMesas);
  $("r-hora").onchange = () => ejecutar(verMesas);
  $("r-fecha").onchange = () => ejecutar(verMesas);
  await verMesas(); await misReservas();
};

/* ----- Cliente: fidelidad (HU-04, HU-05) ----- */
SECCIONES.fidelidad = async (el) => {
  el.innerHTML = `<div class="grid">
    <div class="card"><h2>Mis puntos</h2><p class="sub">Ganas 1 punto por cada $1.000 de consumo, acreditado en caja.</p><div class="big" id="f-puntos">—</div></div>
    <div class="card"><h2>Canjear beneficios</h2><p class="sub">Cambia tus puntos por experiencias.</p><div id="f-bens"></div><div id="f-cupon"></div></div>
  </div>`;
  const nombres = { bebida_gratis: "Bebida gratis", entrada_evento: "Entrada a evento", cena_vip: "Cena VIP", noche_hotel: "Noche de hotel" };
  const cargar = async () => {
    const [p, b] = await Promise.all([api("GET", `/fidelidad/puntos/${encodeURIComponent(sesion.usuario)}`), api("GET", "/fidelidad/beneficios")]);
    $("f-puntos").textContent = p.puntos.toLocaleString("es-CO") + " pts";
    $("f-bens").innerHTML = Object.entries(b).map(([k, c]) => `<div class="ben"><div>${esc(nombres[k] || k)}<br><small>${c} puntos</small></div><button class="btn sm ${p.puntos >= c ? "" : "ghost"}" data-b="${esc(k)}" type="button">Canjear</button></div>`).join("");
    $("f-bens").querySelectorAll("button").forEach((x) => {
      x.onclick = () => ejecutar(async () => {
        const r = await api("POST", "/fidelidad/canjear", { beneficio: x.dataset.b });
        $("f-cupon").innerHTML = `<div class="codigo">${esc(r.cupon)}</div><p class="sub" style="text-align:center;margin-top:8px">Cupón digital · te quedan ${r.puntos_restantes} puntos</p>`;
        toast("Canje exitoso", "good");
        await cargar();
      }, x);
    });
  };
  await cargar();
};

/* ----- Cliente: billetera (HU-06, HU-07) ----- */
SECCIONES.billetera = async (el) => {
  el.innerHTML = `<div class="grid">
    <div class="card"><h2>Saldo disponible</h2><p class="sub">Tu billetera digital.</p><div class="big" id="b-saldo">—</div>
      <label for="b-monto">Monto a recargar (COP)</label><input type="number" id="b-monto" min="1000" step="1000" placeholder="50000">
      <label for="b-metodo">Método de pago</label>
      <select id="b-metodo"><option value="tarjeta">Tarjeta</option><option value="pse">PSE</option><option value="efectivo">Efectivo en caja</option></select>
      <button class="btn" id="b-go" type="button">Recargar</button></div>
    <div class="card"><h2>Últimos movimientos</h2><p class="sub">Máximo 20, del más reciente al más antiguo.</p><div id="b-hist"></div></div>
  </div>`;
  const cargar = async () => {
    const h = await api("GET", `/billetera/${encodeURIComponent(sesion.usuario)}`);
    $("b-saldo").textContent = cop(h.saldo);
    $("b-hist").innerHTML = h.transacciones.length
      ? tabla(["Fecha", "Tipo", "Monto", "Saldo"], h.transacciones.map((t) => `<tr><td>${esc(new Date(t.fecha).toLocaleString("es-CO", { dateStyle: "short", timeStyle: "short" }))}</td><td>${esc(t.tipo)}</td><td>${cop(t.monto)}</td><td>${cop(t.saldo_resultante)}</td></tr>`))
      : vacio("Sin movimientos.");
  };
  alClic("b-go", async () => {
    await api("POST", "/billetera/recarga", { monto: +$("b-monto").value, metodo_pago: $("b-metodo").value });
    toast("Recarga exitosa", "good"); $("b-monto").value = ""; await cargar();
  });
  await cargar();
};

/* ----- Notificaciones (HU-09): cliente ve las suyas; el personal las envía ----- */
SECCIONES.avisos = async (el) => {
  if (sesion.rol === "cliente") {
    el.innerHTML = `<div class="card"><h2>Mis notificaciones</h2><p class="sub">Recordatorios de reserva, promociones y avisos de puntos.</p><button class="btn ghost sm" id="n-recargar" type="button">Actualizar</button><div id="n-lista"></div></div>`;
    const cargar = async () => {
      const ns = await api("GET", `/notificaciones/${encodeURIComponent(sesion.usuario)}`);
      const et = { reserva_proxima: "Reserva próxima", promocion: "Promoción", vencimiento_puntos: "Vencimiento de puntos" };
      $("n-lista").innerHTML = ns.length
        ? ns.map((n) => `<div class="notif"><span class="chip">${esc(et[n.tipo] || n.tipo)}</span> ${esc(n.mensaje)}<small>${esc(new Date(n.enviada_en).toLocaleString("es-CO"))}</small></div>`).join("")
        : vacio("No tienes notificaciones.");
    };
    alClic("n-recargar", cargar);
    await cargar();
    return;
  }
  el.innerHTML = `<div class="grid">
    <div class="card"><h2>Enviar notificación</h2><p class="sub">Push a un cliente (las promociones no se envían a clientes autoexcluidos).</p>
      <label for="n-cliente">Cliente (usuario)</label><input id="n-cliente" placeholder="cliente1">
      <label for="n-tipo">Tipo</label>
      <select id="n-tipo"><option value="promocion">Promoción</option><option value="vencimiento_puntos">Vencimiento de puntos</option><option value="reserva_proxima">Reserva próxima</option></select>
      <label for="n-msg">Mensaje (opcional)</label><input id="n-msg" maxlength="300" placeholder="Si lo dejas vacío se usa el texto por defecto">
      <button class="btn" id="n-enviar" type="button">Enviar</button></div>
    <div class="card"><h2>Recordatorios de reservas</h2><p class="sub">Notifica a los clientes con reservas que empiezan pronto.</p>
      <label for="n-horas">Ventana (horas)</label><input type="number" id="n-horas" min="1" max="48" value="2">
      <button class="btn" id="n-prox" type="button">Enviar recordatorios</button><div id="n-res"></div></div>
  </div>`;
  alClic("n-enviar", async () => {
    const cuerpo = { cliente_id: $("n-cliente").value.trim(), tipo: $("n-tipo").value };
    if ($("n-msg").value.trim()) cuerpo.mensaje = $("n-msg").value.trim();
    await api("POST", "/notificaciones/enviar", cuerpo);
    toast("Notificación enviada", "good");
  });
  alClic("n-prox", async () => {
    const r = await api("POST", `/notificaciones/reservas-proximas?horas=${encodeURIComponent($("n-horas").value || 2)}`);
    $("n-res").innerHTML = `<div class="resultado ${r.length ? "ok" : ""}">${r.length ? r.map((n) => `<div>→ <b>${esc(n.cliente_id)}</b>: ${esc(n.mensaje)}</div>`).join("") : "No hay recordatorios pendientes en esa ventana."}</div>`;
  });
};

/* ----- Cliente: juego responsable (HU-11) ----- */
SECCIONES.responsable = async (el) => {
  el.innerHTML = `<div class="grid">
    <div class="card"><h2>Límite de gasto diario</h2><p class="sub">Juega con control.</p>
      <label for="l-lim">Límite diario (COP)</label><input type="number" id="l-lim" min="1000" step="1000" placeholder="100000">
      <button class="btn ghost" id="l-set" type="button">Definir límite</button>
      <label for="l-gasto">Registrar un gasto (COP)</label><input type="number" id="l-gasto" min="1000" step="1000" placeholder="30000">
      <button class="btn" id="l-go" type="button">Registrar gasto</button></div>
    <div class="card"><h2>Autoexclusión</h2><p class="sub">Bloquea tu cuenta durante el periodo que elijas. <b>No se puede cancelar ni acortar.</b></p>
      <div id="a-estado"></div>
      <label for="a-dias">Duración en días</label><input type="number" id="a-dias" min="1" max="3650" value="30">
      <button class="btn danger" id="a-go" type="button">Activar autoexclusión</button></div>
  </div>`;
  const estado = async () => {
    const a = await api("GET", `/fidelidad/autoexclusion/${encodeURIComponent(sesion.usuario)}`);
    $("a-estado").innerHTML = a.activa ? `<span class="chip warn">Autoexcluido hasta ${esc(a.bloqueado_hasta)}</span>` : '<span class="chip ok">Sin autoexclusión</span>';
  };
  alClic("l-set", async () => { await api("POST", "/fidelidad/limite", { limite_diario: +$("l-lim").value }); toast("Límite diario definido", "good"); });
  alClic("l-go", async () => {
    const r = await api("POST", "/fidelidad/gasto", { monto: +$("l-gasto").value });
    toast(r.permitido ? `Gasto registrado · hoy llevas ${cop(r.gastado_hoy)}` : r.mensaje, r.permitido ? "good" : "err");
  });
  alClic("a-go", async () => {
    if (!confirm("La autoexclusión NO se puede cancelar ni acortar. ¿Continuar?")) return;
    const r = await api("POST", "/fidelidad/autoexclusion", { dias: +$("a-dias").value });
    toast("Cuenta bloqueada hasta " + r.bloqueado_hasta, "good"); await estado();
  });
  await estado();
};

/* ----- Anfitrión / gerente: reservas del día y check-in (HU-03) ----- */
SECCIONES.agenda = async (el) => {
  el.innerHTML = `<div class="grid">
    <div class="card ancha"><h2>Reservas del día</h2><p class="sub">Vista del anfitrión para gestionar el check-in.</p>
      <div class="row">
        <div><label for="g-fecha">Fecha</label><input type="date" id="g-fecha" value="${hoy()}"></div>
        <div><label for="g-codigo">Check-in por código</label><input id="g-codigo" maxlength="8" placeholder="Ej. DEMO0001"></div>
        <div class="acciones"><button class="btn" id="g-checkin" type="button">Hacer check-in</button></div>
      </div>
      <div id="g-lista"></div></div>
  </div>`;
  const cargar = async () => {
    const f = $("g-fecha").value;
    const rs = await api("GET", "/reservas" + (f ? `?fecha=${f}` : ""));
    $("g-lista").innerHTML = rs.length
      ? tabla(["Hora", "Mesa", "Cliente", "Código", "Estado", ""], rs.map((r) => `<tr><td>${esc(r.hora)}</td><td>${r.mesa_id}</td><td>${esc(r.cliente_id)}</td><td><b>${esc(r.codigo_confirmacion)}</b></td><td>${estadoChip(r.estado)}</td><td>${r.estado === "confirmada" ? `<button class="btn sm" data-cod="${esc(r.codigo_confirmacion)}" type="button">Check-in</button>` : ""}</td></tr>`))
      : vacio("Sin reservas para esta fecha.");
    $("g-lista").querySelectorAll("button[data-cod]").forEach((b) => { b.onclick = () => ejecutar(() => checkin(b.dataset.cod), b); });
  };
  const checkin = async (codigo) => {
    const r = await api("POST", "/reservas/checkin", { codigo_confirmacion: codigo });
    toast(`Check-in realizado · mesa ${r.mesa_id} (${r.cliente_id})`, "good");
    await cargar();
  };
  alClic("g-checkin", async () => { await checkin($("g-codigo").value); $("g-codigo").value = ""; });
  $("g-fecha").onchange = () => ejecutar(cargar);
  await cargar();
};

/* ----- Cajero / gerente: caja (HU-04, HU-06, HU-08) ----- */
SECCIONES.caja = async (el) => {
  const metodos = '<option value="efectivo">Efectivo</option><option value="tarjeta">Tarjeta</option><option value="pse">PSE</option>';
  el.innerHTML = `<div class="grid">
    <div class="card"><h2>Validar saldo</h2><p class="sub">Autoriza operaciones con fichas.</p>
      <label for="c-cli1">Cliente (usuario)</label><input id="c-cli1" placeholder="cliente1">
      <label for="c-monto1">Monto requerido (COP)</label><input type="number" id="c-monto1" min="0" step="1000" placeholder="50000">
      <button class="btn" id="c-validar" type="button">Validar</button><div id="c-res1"></div></div>
    <div class="card"><h2>Registrar consumo</h2><p class="sub">Acredita puntos automáticamente (1 por cada $1.000).</p>
      <label for="c-cli2">Cliente (usuario)</label><input id="c-cli2" placeholder="cliente1">
      <label for="c-monto2">Consumo (COP)</label><input type="number" id="c-monto2" min="1000" step="1000" placeholder="120000">
      <button class="btn" id="c-acum" type="button">Acreditar puntos</button><div id="c-res2"></div></div>
    <div class="card"><h2>Recarga en caja</h2><p class="sub">Recarga la billetera de un cliente.</p>
      <label for="c-cli3">Cliente (usuario)</label><input id="c-cli3" placeholder="cliente1">
      <label for="c-monto3">Monto (COP)</label><input type="number" id="c-monto3" min="1000" step="1000" placeholder="50000">
      <label for="c-met3">Método de pago</label><select id="c-met3">${metodos}</select>
      <button class="btn" id="c-rec" type="button">Recargar</button><div id="c-res3"></div></div>
  </div>`;
  alClic("c-validar", async () => {
    const q = new URLSearchParams({ cliente_id: $("c-cli1").value.trim(), monto_requerido: $("c-monto1").value || 0 });
    const r = await api("GET", "/billetera/validar?" + q);
    $("c-res1").innerHTML = `<div class="resultado ${r.valido ? "ok" : "no"}"><b>${r.valido ? "✔ Saldo suficiente" : "✘ Saldo insuficiente"}</b><br>Disponible: ${cop(r.saldo_disponible)} · Requerido: ${cop(r.monto_requerido)}</div>`;
  });
  alClic("c-acum", async () => {
    const r = await api("POST", "/fidelidad/acumular", { cliente_id: $("c-cli2").value.trim(), monto_gastado: +$("c-monto2").value });
    $("c-res2").innerHTML = `<div class="resultado ok">+${r.puntos_ganados} puntos · total ${r.puntos_totales}</div>`;
    toast("Puntos acreditados", "good");
  });
  alClic("c-rec", async () => {
    const r = await api("POST", "/billetera/recarga", { cliente_id: $("c-cli3").value.trim(), monto: +$("c-monto3").value, metodo_pago: $("c-met3").value });
    $("c-res3").innerHTML = `<div class="resultado ok">Nuevo saldo de ${esc(r.cliente_id)}: ${cop(r.saldo)}</div>`;
    toast("Recarga registrada", "good");
  });
};

/* ----- Gerente: reportes (HU-12) ----- */
SECCIONES.reportes = async (el) => {
  el.innerHTML = `<div class="card"><h2>Reporte de transacciones</h2><p class="sub">Recargas y movimientos del periodo, exportables en CSV.</p>
    <div class="row">
      <div><label for="rp-ini">Desde</label><input type="date" id="rp-ini"></div>
      <div><label for="rp-fin">Hasta</label><input type="date" id="rp-fin"></div>
      <div class="acciones"><button class="btn" id="rp-ver" type="button">Ver reporte</button><button class="btn ghost" id="rp-bajar" type="button">Descargar CSV</button></div>
    </div><div id="rp-res"></div></div>`;
  const consulta = () => {
    const q = new URLSearchParams();
    if ($("rp-ini").value) q.set("fecha_inicio", $("rp-ini").value);
    if ($("rp-fin").value) q.set("fecha_fin", $("rp-fin").value);
    return "/billetera/reportes" + (q.toString() ? "?" + q : "");
  };
  const parsear = (csv) => csv.trim().split("\n").map((l) => l.split(","));
  alClic("rp-ver", async () => {
    const filas = parsear(await (await api("GET", consulta(), undefined, { blob: true })).text());
    const [cab, ...datos] = filas;
    $("rp-res").innerHTML = datos.length
      ? `<p class="sub" style="margin-top:14px">${datos.length} transacciones</p>` + tabla(cab, datos.map((f) => `<tr>${f.map((c, i) => `<td>${esc(i === 4 ? new Date(c).toLocaleString("es-CO") : c)}</td>`).join("")}</tr>`))
      : vacio("No hay transacciones en ese periodo.");
  });
  alClic("rp-bajar", async () => {
    const blob = await api("GET", consulta(), undefined, { blob: true });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = "reporte_billetera.csv"; a.click();
    URL.revokeObjectURL(a.href);
    toast("Reporte descargado", "good");
  });
};

/* ---------------- navegación y arranque ---------------- */
function irA(seccion) {
  document.querySelectorAll("#nav button").forEach((b) => b.classList.toggle("on", b.dataset.s === seccion));
  const el = $("contenido");
  el.innerHTML = "";
  ejecutar(() => SECCIONES[seccion](el));
}
function mostrarApp() {
  $("vista-login").hidden = true;
  $("vista-app").hidden = false;
  $("quien").innerHTML = `<b>${esc(sesion.nombre)}</b> · ${esc(ROLES[sesion.rol] || sesion.rol)}`;
  $("subtitulo").textContent = "Casino · " + (ROLES[sesion.rol] || "");
  const secciones = NAV[sesion.rol] || [];
  $("nav").innerHTML = secciones.map(([id, t]) => `<button type="button" data-s="${id}">${esc(t)}</button>`).join("");
  $("nav").querySelectorAll("button").forEach((b) => { b.onclick = () => irA(b.dataset.s); });
  irA(secciones[0][0]);
}
function mostrarLogin() {
  $("vista-app").hidden = true;
  $("vista-login").hidden = false;
  $("l-pass").value = "";
}

async function iniciarSesion(usuario, password) {
  const r = await api("POST", "/auth/login", { usuario, password }, { auth: false });
  guardarSesion({ token: r.access_token, usuario: r.usuario, nombre: r.nombre, rol: r.rol });
  mostrarApp();
}

function configurarLogin() {
  const demo = [["cliente1", "Cliente"], ["cliente2", "Cliente 2"], ["anfitrion", "Anfitrión"], ["cajero", "Cajero"], ["gerente", "Gerente"]];
  $("demo-chips").innerHTML = demo.map(([u, t]) => `<button type="button" data-u="${u}">${t}</button>`).join("");
  $("demo-chips").querySelectorAll("button").forEach((b) => {
    b.onclick = () => { $("l-user").value = b.dataset.u; $("l-pass").value = "Casino2026!"; };
  });
  const cambiar = (entrar) => {
    $("f-login").hidden = !entrar; $("f-registro").hidden = entrar;
    $("t-entrar").classList.toggle("on", entrar); $("t-crear").classList.toggle("on", !entrar);
  };
  $("t-entrar").onclick = () => cambiar(true);
  $("t-crear").onclick = () => cambiar(false);
  $("r-nac").max = hoy();

  $("f-login").onsubmit = (e) => {
    e.preventDefault();
    ejecutar(() => iniciarSesion($("l-user").value.trim(), $("l-pass").value), e.submitter);
  };
  $("f-registro").onsubmit = (e) => {
    e.preventDefault();
    ejecutar(async () => {
      const cuerpo = { nombre: $("r-nombre").value.trim(), usuario: $("r-user").value.trim().toLowerCase(), documento: $("r-doc").value.trim(), fecha_nacimiento: $("r-nac").value, password: $("r-pass").value };
      await api("POST", "/usuarios/registro", cuerpo, { auth: false });
      toast("Cuenta creada. ¡Bienvenido!", "good");
      await iniciarSesion(cuerpo.usuario, cuerpo.password);
    }, e.submitter);
  };
  $("salir").onclick = () => cerrarSesion();
}

configurarLogin();
// La documentación Swagger está en el puerto del API (8000), no detrás del proxy /api.
$("enlace-docs").href = `${location.protocol}//${location.hostname}:8000/docs`;
const guardada = leerSesion();
if (guardada && guardada.token) {
  sesion = guardada;
  // Comprueba que el token siga siendo válido antes de mostrar la app.
  api("GET", "/auth/me").then(mostrarApp).catch(() => mostrarLogin());
} else {
  mostrarLogin();
}
