/*! coi-serviceworker v0.1.7 - Guido Zuidhof and contributors, licensed under MIT */
let coepCredentialless = false;
if (typeof window === 'undefined') {
    self.addEventListener("install", () => self.skipWaiting());
    self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

    self.addEventListener("message", (ev) => {
        if (!ev.data) {
            return;
        } else if (ev.data.type === "deregister") {
            self.registration.unregister().then(() => {
                return self.clients.matchAll();
            }).then(clients => {
                clients.forEach((client) => client.navigate(client.url));
            });
        } else if (ev.data.type === "coepCredentialless") {
            coepCredentialless = ev.data.value;
        }
    });

    self.addEventListener("fetch", function (event) {
        if (event.request.cache === "only-if-cached" && event.request.mode !== "same-origin") {
            return;
        }

        const request = (coepCredentialless && event.request.mode === "no-cors")
            ? new Request(event.request, { credentials: "omit" })
            : event.request;

        event.respondWith(
            fetch(request).then((response) => {
                if (response.status === 0) {
                    return response;
                }

                const newHeaders = new Headers(response.headers);
                newHeaders.set("Cross-Origin-Embedder-Policy",
                    coepCredentialless ? "credentialless" : "require-corp"
                );
                if (!coepCredentialless) {
                    newHeaders.set("Cross-Origin-Resource-Policy", "cross-origin");
                }
                newHeaders.set("Cross-Origin-Opener-Policy", "same-origin");

                return new Response(response.body, {
                    status: response.status,
                    statusText: response.statusText,
                    headers: newHeaders,
                });
            }).catch((e) => console.error(e))
        );
    });
} else {
    (() => {
        const reload = () => window.location.reload();

        try {
            const registration = window.navigator.serviceWorker.register(window.document.currentScript.src);
            registration.then(ready => {
                ready.addEventListener("updatefound", () => {
                    console.log("Service Worker update found.");
                    ready.installing.addEventListener("statechange", () => {
                        if (ready.installing.state === "activated") {
                            console.log("Service Worker activated.");
                            reload();
                        }
                    });
                });
            });
            let isMacSafari = (window.navigator.userAgent.indexOf("Safari") !== -1) &&
                (window.navigator.userAgent.indexOf("Mac") !== -1) &&
                (window.navigator.userAgent.indexOf("Chrome") === -1);
            if (isMacSafari) {
                navigator.serviceWorker.ready.then((registration) => {
                    registration.active.postMessage({
                        type: "coepCredentialless",
                        value: false
                    });
                });
            }
        } catch (e) {
            console.error("COI Service Worker registration failed", e);
        }

        if (window.crossOriginIsolated !== false) return;

        window.navigator.serviceWorker.addEventListener("controllerchange", () => {
            if (!window.crossOriginIsolated) {
                console.log("Reloading page to apply COOP/COEP headers.");
                reload();
            }
        });
    })();
}
