/** @odoo-module **/

/**
 * Script de Firma Digital para Portal de Waybills (JS Plano y Robusto)
 *
 * 1. Inicializa canvas al mostrar el modal (shown.bs.modal).
 * 2. Maneja dibujo con Pointer Events (mouse/touch/pen).
 * 3. Permite generar firma con nombre (texto cursivo).
 * 4. Valida y guarda base64 puro en hidden input.
 * 5. Evita conflictos de listeners duplicados.
 */

(function() {
    'use strict';

    function initSignatureModal() {
        console.log('TMS Portal Sign: Inicializando script...');

        // ================================================================
        // A) SETUP AL ABRIR MODAL
        // ================================================================
        const modalEl = document.getElementById('signModal');

        if (modalEl) {
            console.log('TMS Portal Sign: Modal encontrado #signModal');

            // Usar una bandera para no duplicar el listener del modal
            if (!modalEl.dataset.signatureInitialized) {
                modalEl.addEventListener('shown.bs.modal', function () {
                    console.log('TMS Portal Sign: Modal mostrado (shown.bs.modal)');

                    // Referencias a elementos dentro del modal
                    const canvas = document.getElementById('signatureCanvas');
                    const dataInput = document.getElementById('signature_data');
                    const nameInput = document.getElementById('signature_name');
                    const clearBtn = document.getElementById('clearSignature');
                    const generateBtn = document.getElementById('generateSignatureBtn');
                    const form = modalEl.querySelector('form[action*="/sign"]'); // Updated form selector

                    if (!canvas) {
                        console.error('TMS Portal Sign: Canvas no encontrado dentro del modal');
                        return;
                    }

                    // Auto-Focus al nombre cuando se abre
                    if (nameInput) nameInput.focus();

                    // Intentar obtener geolocalización
                    try {
                        if ("geolocation" in navigator) {
                            navigator.geolocation.getCurrentPosition(function(position) {
                                const latInput = document.getElementById('signed_latitude');
                                const longInput = document.getElementById('signed_longitude');
                                if (latInput && longInput) {
                                    latInput.value = position.coords.latitude;
                                    longInput.value = position.coords.longitude;
                                    console.log("Ubicación capturada:", position.coords.latitude, position.coords.longitude);
                                }
                            }, function(error) {
                                console.warn("Error obteniendo ubicación:", error.message);
                            }, {
                                enableHighAccuracy: true,
                                timeout: 5000,
                                maximumAge: 0
                            });
                        } else {
                            console.log("Geolocalización no disponible en este navegador.");
                        }
                    } catch (e) {
                        console.error("Error al intentar obtener geolocalización:", e);
                    }

                    // 1. Configurar canvas (tamaño real, contexto, estilo)
                    setupCanvas(canvas);

                    // 2. Bindear eventos de dibujo (solo una vez)
                    bindCanvasEventsOnce(canvas);

                    // 3. Sincronizar UI (mostrar/ocultar botón generar según radio)
                    syncMethodUI();

                    // 4. Bindear eventos de UI

                    if (clearBtn && !clearBtn.dataset.bound) {
                        clearBtn.addEventListener('click', function(e) {
                            e.preventDefault();
                            clearCanvas(canvas);
                        });
                        clearBtn.dataset.bound = '1';
                    }

                    if (generateBtn && !generateBtn.dataset.bound) {
                        generateBtn.addEventListener('click', function(e) {
                            e.preventDefault();
                            generateSignatureFromName(canvas, nameInput);
                        });
                        generateBtn.dataset.bound = '1';
                    }

                    if (nameInput && !nameInput.dataset.bound) {
                        nameInput.addEventListener('input', function(e) {
                            const generatedRadio = document.getElementById('signMethodGenerated');
                            if (generatedRadio && generatedRadio.checked) {
                                generateSignatureFromName(canvas, nameInput);
                            }
                        });
                        nameInput.dataset.bound = '1';
                    }

                    // Radios - cambio de método
                    const radios = modalEl.querySelectorAll('input[name="signMethod"]');
                    radios.forEach(radio => {
                        if (!radio.dataset.bound) {
                            radio.addEventListener('change', () => syncMethodUI(canvas, nameInput));
                            radio.dataset.bound = '1';
                        }
                    });

                    // Submit del formulario
                    if (form && !form.dataset.bound) {
                        form.addEventListener('submit', function(e) {
                            if (!validateAndSubmit(e, canvas, nameInput, dataInput)) {
                                e.preventDefault();
                            }
                        });
                        form.dataset.bound = '1';
                    }
                });

                // Marcar modal como inicializado para no re-agregar listener
                modalEl.dataset.signatureInitialized = '1';
            }
        } else {
            console.warn('TMS Portal Sign: Modal #signModal no encontrado en el DOM');
        }
    }

    // ================================================================
    // B) SETUP CANVAS
    // ================================================================
    function setupCanvas(canvas, tries = 0) {
        const rect = canvas.getBoundingClientRect();
        console.log(`TMS Portal Sign: Setup canvas intento ${tries}, width=${rect.width}, height=${rect.height}`);

        // Reintentar si el tamaño es 0 (puede pasar si el modal aún anima)
        if (rect.width <= 0 || rect.height <= 0) {
            if (tries < 10) {
                requestAnimationFrame(() => setupCanvas(canvas, tries + 1));
            }
            return;
        }

        const dpr = window.devicePixelRatio || 1;

        // Configurar tamaño interno REAL
        canvas.width = Math.floor(rect.width * dpr);
        canvas.height = Math.floor(rect.height * dpr);

        const ctx = canvas.getContext('2d');

        // Escalar sistema de coordenadas
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

        // Configurar estilo del trazo
        ctx.lineWidth = 2.5;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.strokeStyle = '#111';

        // Llenar con fondo blanco (importante para evitar transparencia en PNG)
        ctx.clearRect(0, 0, rect.width, rect.height);
        ctx.fillStyle = "#fff";
        ctx.fillRect(0, 0, rect.width, rect.height);

        // Resetear banderas globales/dataset del canvas
        canvas.dataset.hasSignature = 'false';

        // Limpiar input hidden
        const dataInput = document.getElementById('signature_data');
        if (dataInput) dataInput.value = "";
    }

    // ================================================================
    // C) DIBUJO MANUAL (POINTER EVENTS)
    // ================================================================
    function bindCanvasEventsOnce(canvas) {
        if (canvas.dataset.eventsBound) return;
        console.log('TMS Portal Sign: Bindeando eventos de puntero');

        let isDrawing = false;

        function startDrawing(e) {
            // Solo permitir dibujo si está seleccionado "manual"
            const manualRadio = document.getElementById('signMethodManual');
            if (manualRadio && !manualRadio.checked) return;

            // IMPORTANTE: Prevenir que el navegador tome el control (scrolling)
            if (e.cancelable) e.preventDefault();
            e.stopPropagation();

            try {
                canvas.setPointerCapture(e.pointerId);
            } catch (err) {
                console.warn('Error en setPointerCapture', err);
            }

            isDrawing = true;

            const rect = canvas.getBoundingClientRect();
            // Coordenadas relativas al canvas (CSS pixels)
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            const ctx = canvas.getContext('2d');
            ctx.beginPath();
            ctx.moveTo(x, y);

            console.log('Start drawing at', x, y);
        }

        function draw(e) {
            if (!isDrawing) return;

            if (e.cancelable) e.preventDefault();
            e.stopPropagation();

            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            const ctx = canvas.getContext('2d');
            ctx.lineTo(x, y);
            ctx.stroke();

            canvas.dataset.hasSignature = 'true';
        }

        function stopDrawing(e) {
            if (isDrawing) {
                isDrawing = false;
                const ctx = canvas.getContext('2d');
                ctx.closePath();
                if (e.pointerId) {
                    try {
                        canvas.releasePointerCapture(e.pointerId);
                    } catch (err) {
                         // Ignorar si el puntero ya no es válido
                    }
                }
                console.log('Stop drawing');
            }
        }

        canvas.addEventListener('pointerdown', startDrawing);
        canvas.addEventListener('pointermove', draw);
        canvas.addEventListener('pointerup', stopDrawing);
        canvas.addEventListener('pointercancel', stopDrawing);
        // Eventos extra por seguridad en touch devices antiguos
        canvas.addEventListener('touchstart', (e) => { if(e.cancelable) e.preventDefault(); }, {passive: false});

        canvas.dataset.eventsBound = '1';
    }

    // ================================================================
    // D) GENERAR FIRMA CON NOMBRE
    // ================================================================
    function generateSignatureFromName(canvas, nameInput) {
        const name = nameInput.value.trim();

        // Limpiar canvas siempre antes de (re)generar
        setupCanvas(canvas);

        if (!name) {
            // Si está vacío, solo limpiamos (ya hecho arriba) y salimos
            // Se reseteó hasSignature a false en setupCanvas
            return;
        }

        const ctx = canvas.getContext('2d');
        const rect = canvas.getBoundingClientRect();
        const width = rect.width;
        const height = rect.height;

        // Fuente base
        let fontSize = 52;
        const fontBase = "'Segoe Script','Brush Script MT','Lucida Handwriting',cursive";

        ctx.fillStyle = "#111"; // Color texto
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";

        // Ajustar tamaño de fuente
        do {
            ctx.font = `italic ${fontSize}px ${fontBase}`;
            const textWidth = ctx.measureText(name).width;
            if (textWidth < (width - 40)) break;
            fontSize -= 2;
        } while (fontSize > 16);

        // Guardar estado, transformar (inclinación), dibujar, restaurar
        ctx.save();
        ctx.transform(1, 0, -0.18, 1, 0, 0);
        ctx.fillText(name, width / 2, height / 2);
        ctx.restore();

        canvas.dataset.hasSignature = 'true';

        // Actualizar hidden inmediatamente
        updateHidden(canvas);
        console.log('Firma generada con nombre:', name);
    }

    // ================================================================
    // E) ACTUALIZAR HIDDEN BASE64
    // ================================================================
    function updateHidden(canvas) {
        const dataInput = document.getElementById('signature_data');
        if (!dataInput) return;

        const dataUrl = canvas.toDataURL("image/png");
        dataInput.value = dataUrl.split(",")[1];
    }

    // ================================================================
    // F) SUBMIT / VALIDACIÓN
    // ================================================================
    function validateAndSubmit(e, canvas, nameInput, dataInput) {
        // Validar nombre
        const name = nameInput.value.trim();
        if (!name) {
            alert("El nombre es obligatorio.");
            nameInput.focus();
            return false;
        }

        // Validar si hay firma
        if (canvas.dataset.hasSignature !== 'true') {
            alert("Debe firmar (dibujar o escribir su nombre) para continuar.");
            return false;
        }

        // Actualizar el valor hidden justo antes de enviar
        updateHidden(canvas);

        if (!dataInput.value) {
            alert("Error al generar los datos de la firma. Intente nuevamente.");
            return false;
        }

        console.log('Submit validado, enviando formulario...');
        return true;
    }

    // ================================================================
    // G) LIMPIAR
    // ================================================================
    function clearCanvas(canvas) {
        console.log('Limpiando canvas...');
        setupCanvas(canvas);
    }

    // ================================================================
    // H) RADIOS / UI
    // ================================================================
    function syncMethodUI(canvas, nameInput) {
        const generatedRadio = document.getElementById('signMethodGenerated');
        const generateBtn = document.getElementById('generateSignatureBtn');
        const hint = document.getElementById('signatureHint');

        // Referencias opcionales si no se pasan (para llamadas iniciales)
        if (!canvas) canvas = document.getElementById('signatureCanvas');
        if (!nameInput) nameInput = document.getElementById('signature_name');

        if (generatedRadio && generatedRadio.checked) {
            // Modo Generado: Ocultar botón, firma automática al escribir
            if (generateBtn) generateBtn.style.display = 'none';
            if (hint) hint.textContent = "Escriba su nombre para ver su firma generada automáticamente.";

            // Trigger inicial por si ya hay texto
            if (nameInput && nameInput.value) {
                generateSignatureFromName(canvas, nameInput);
            } else {
                // Si no hay texto, asegurar canvas limpio (o dejar lo que estaba?)
                // Mejor limpiar para evitar confusión
                clearCanvas(canvas);
            }
        } else {
            // Modo Manual
            if (generateBtn) generateBtn.style.display = 'none'; // Tampoco lo mostramos en manual
            if (hint) hint.textContent = "Dibuje su firma en el recuadro superior";

            // Limpiar canvas al cambiar a manual para evitar firma generada "pegada"
            clearCanvas(canvas);
        }
    }

    // ================================================================
    // INICIALIZACIÓN ROBUSTA (Check readyState)
    // ================================================================
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSignatureModal);
    } else {
        // DOM ya cargado
        initSignatureModal();
    }

})();
