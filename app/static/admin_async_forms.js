(() => {
    if (window.__adminAsyncFormsReady) return;
    window.__adminAsyncFormsReady = true;

    const adminMain = () => document.querySelector(".admin-main");
    const excludedPath = /\/(descargar|excel|pdf|exportar|suplantar)(\/|$)/i;

    const showNotice = (message, tone = "success") => {
        let notice = document.querySelector("[data-admin-async-notice]");
        if (!notice) {
            notice = document.createElement("div");
            notice.dataset.adminAsyncNotice = "";
            document.body.appendChild(notice);
        }
        notice.className = `account-async-notice ${tone}`;
        notice.textContent = message;
        notice.hidden = false;
        window.clearTimeout(notice._hideTimer);
        notice._hideTimer = window.setTimeout(() => { notice.hidden = true; }, 4500);
    };

    const stateKey = (control, index) => control.id || control.name || `control-${index}`;
    const captureViewState = () => {
        const state = {};
        const selector = [
            "input[type='search']", "[data-judge-filter-search]", "[data-judge-filter-category]",
            "[data-judge-filter-english]", "[data-judge-filter-scope]", "[data-judge-filter-active]",
            "[data-assignment-filter]", "[data-project-filter]"
        ].join(",");
        adminMain()?.querySelectorAll(selector).forEach((control, index) => {
            if (!control.closest("dialog")) state[stateKey(control, index)] = control.value;
        });
        return state;
    };

    const restoreViewState = (state) => {
        const controls = adminMain()?.querySelectorAll("input[type='search'], select, input[type='radio']") || [];
        controls.forEach((control, index) => {
            const key = stateKey(control, index);
            if (!(key in state) || control.closest("dialog")) return;
            if (control.type === "radio") control.checked = control.value === state[key];
            else control.value = state[key];
            control.dispatchEvent(new Event("input", {bubbles: true}));
            control.dispatchEvent(new Event("change", {bubbles: true}));
        });
    };

    const activatePageScripts = (container) => {
        let needsReadyEvent = false;
        container.querySelectorAll("script").forEach((oldScript) => {
            if (oldScript.src) return;
            const code = oldScript.textContent || "";
            if (!code.trim()) return;
            if (code.includes("DOMContentLoaded")) {
                needsReadyEvent = true;
                return;
            }
            if (code.includes("document.addEventListener") || code.includes("window.addEventListener")) return;
            const script = document.createElement("script");
            script.textContent = code;
            document.body.appendChild(script);
            script.remove();
        });
        if (needsReadyEvent) document.dispatchEvent(new Event("DOMContentLoaded"));
    };

    const replaceAdminContent = (html, state, scrollPosition) => {
        const parsed = new DOMParser().parseFromString(html, "text/html");
        const replacement = parsed.querySelector(".admin-main");
        const current = adminMain();
        if (!replacement || !current) throw new Error("No se pudo actualizar el contenido del panel.");
        current.innerHTML = replacement.innerHTML;
        activatePageScripts(current);
        restoreViewState(state);
        history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
        window.scrollTo(scrollPosition.x, scrollPosition.y);
    };

    const shouldHandle = (form, event) => {
        if (event.defaultPrevented || !adminMain()?.contains(form)) return false;
        if ((form.method || "get").toLowerCase() !== "post") return false;
        if (form.matches("[data-admin-async-off], [data-gitops-reload-form], [data-whatsapp-mark-form]")) return false;
        if (form.target && form.target !== "_self") return false;
        const actionUrl = new URL(form.action || window.location.href, window.location.href);
        if (actionUrl.origin !== window.location.origin || excludedPath.test(actionUrl.pathname)) return false;
        return true;
    };

    document.addEventListener("submit", async (event) => {
        const form = event.target.closest("form");
        if (!form || !shouldHandle(form, event)) return;
        event.preventDefault();
        const button = event.submitter || form.querySelector("button[type='submit'], input[type='submit']");
        const previousContent = button?.innerHTML;
        const state = captureViewState();
        const scrollPosition = {x: window.scrollX, y: window.scrollY};
        const actionUrl = new URL(form.action || window.location.href, window.location.href);
        const formData = new FormData(form);
        const usesAdminActionApi = actionUrl.pathname.endsWith("/admin/action");
        if (usesAdminActionApi) formData.set("batch_mode", "1");
        if (button) { button.disabled = true; button.textContent = "Procesando…"; }
        try {
            let response = await fetch(actionUrl.href, {
                method: "POST",
                headers: {"Accept": usesAdminActionApi ? "application/json" : "text/html", "X-Requested-With": "XMLHttpRequest"},
                body: formData
            });
            let serverMessage = "";
            if (usesAdminActionApi) {
                const contentType = response.headers.get("content-type") || "";
                if (!contentType.includes("application/json")) throw new Error("El servidor no confirmó la acción correctamente.");
                const payload = await response.json();
                serverMessage = payload.messages?.map((item) => item.message).filter(Boolean).join(" ") || "";
                if (!response.ok || !payload.ok) throw new Error(serverMessage || payload.error || "No se pudo completar la acción.");
                response = await fetch(`${window.location.pathname}${window.location.search}`, {
                    headers: {"Accept": "text/html", "X-Requested-With": "XMLHttpRequest"},
                    cache: "no-store"
                });
            }
            if (!response.ok) throw new Error(`No se pudo actualizar la vista (HTTP ${response.status}).`);
            const contentType = response.headers.get("content-type") || "";
            if (!contentType.includes("text/html")) throw new Error("La actualización no devolvió la vista del panel.");
            const html = await response.text();
            const parsed = new DOMParser().parseFromString(html, "text/html");
            const alerts = [...parsed.querySelectorAll(".alert")];
            const error = alerts.find((item) => item.classList.contains("error"));
            if (error) throw new Error(error.textContent.trim());
            replaceAdminContent(html, state, scrollPosition);
            const message = serverMessage || alerts.map((item) => item.textContent.trim()).filter(Boolean).join(" ");
            showNotice(message || "Cambio guardado. Puedes continuar trabajando.");
        } catch (error) {
            showNotice(error.message || "No se pudo completar la acción.", "error");
        } finally {
            if (button?.isConnected) { button.disabled = false; button.innerHTML = previousContent; }
        }
    });
})();
