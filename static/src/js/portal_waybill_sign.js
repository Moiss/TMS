/** @odoo-module **/

/**
 * Script de Firma Digital para Portal de Waybills
 *
 * IDs REALES (documentados para referencia):
 * - Modal Bootstrap: #signModal
 * - Canvas: #signatureCanvas
 * - Hidden base64: #signature_data
 * - Input Nombre: #signature_name
 * - Radios: #signMethodManual, #signMethodGenerated
 * - Botones: #clearSignature, #generateSignatureBtn
 * - Submit: #confirmSignBtn
 * - Hint: #signatureHint
 *
 * FUNCIONALIDAD:
 * - Captura firma dibujada con Pointer Events (mouse + touch unificado)
 * - Genera firma con nombre en letra cursiva
 * - Inicializa canvas solo cuando el modal está visible
 * - Escalado High DPI / Retina
 * - Convierte a base64 PNG antes del submit
 */

import { publicWidget } from "@web/legacy/js/public/public_widget";

publicWidget.registry.PortalWaybillSign = publicWidget.Widget.extend({
    selector: '#signModal',

    /**
     * Se ejecuta cuando el widget se inicializa (al cargar la página)
     */
    start: function() {
        const self = this;

        // Obtener elementos del DOM
        const modalEl = this.el; // #signModal
        const canvas = modalEl.querySelector('#signatureCanvas');
        const signForm = modalEl.querySelector('form');

        // Si no existe el canvas, salir
        if (!canvas) {
            console.debug('TMS Portal Sign: Canvas no encontrado');
            return this._super.apply(this, arguments);
        }

        // ================================================================
        // 2.1 VARIABLES DE ESTADO (una sola instancia)
        // ================================================================
        let ctx = null;              // Contexto 2D del canvas
        let isDrawing = false;       // Indica si el usuario está dibujando
        let hasSignature = false;    // Indica si hay trazo o texto generado
        let dpr = 1;                 // Device Pixel Ratio (para High DPI)
        let setupTries = 0;          // Contador de intentos de setup (máximo 10)

        // ================================================================
        // 2.2 HELPERS (funciones auxiliares)
        // ================================================================

        /**
         * Obtiene el rect del canvas (bounding client rect)
         * @returns {DOMRect} Rectángulo del canvas en coordenadas de viewport
         */
        function getRect() {
            return canvas.getBoundingClientRect();
        }

        /**
         * Obtiene las coordenadas del punto del evento relativas al canvas
         * @param {PointerEvent} ev - Evento pointer
         * @returns {Object} Objeto con {x, y, r} donde r es el rect
         */
        function getPoint(ev) {
            const r = getRect();
            return {
                x: ev.clientX - r.left,
                y: ev.clientY - r.top,
                r: r
            };
        }

        // ================================================================
        // 2.3 SETUPCANVAS() - CRÍTICO: solo cuando el modal está visible
        // ================================================================

        /**
         * Configura el canvas con tamaño correcto y contexto 2D
         * CRÍTICO: Se ejecuta cuando el modal está visible para obtener tamaño correcto
         */
        function setupCanvas() {
            // Obtener el rect del canvas (tamaño visual en pantalla)
            const rect = canvas.getBoundingClientRect();

            // Validar que el canvas tenga tamaño válido (no 0x0)
            // Si el modal está oculto, rect.width y rect.height pueden ser 0
            if (rect.width <= 0 || rect.height <= 0) {
                setupTries++;
                // Reintentar hasta máximo 10 veces
                if (setupTries < 10) {
                    // Usar requestAnimationFrame para reintentar en el próximo frame
                    requestAnimationFrame(setupCanvas);
                    return;
                } else {
                    console.warn('TMS Portal Sign: No se pudo inicializar el canvas después de 10 intentos');
                    return;
                }
            }

            // Obtener device pixel ratio (para High DPI / Retina)
            dpr = window.devicePixelRatio || 1;

            // Ajustar tamaño interno del canvas (NO solo CSS)
            // Math.floor para evitar problemas de subpíxeles
            canvas.width = Math.floor(rect.width * dpr);
            canvas.height = Math.floor(rect.height * dpr);

            // Obtener contexto 2D
            ctx = canvas.getContext('2d');

            // Transform fijo (evita acumulación de transformaciones)
            // Esto escala el contexto para que coincida con el tamaño visual
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

            // Configurar estilo del trazo (para dibujo manual)
            ctx.lineWidth = 2.5;           // Grosor del trazo
            ctx.lineCap = 'round';         // Extremos redondeados
            ctx.lineJoin = 'round';        // Uniones redondeadas
            ctx.strokeStyle = '#111';      // Color negro (casi negro para mejor contraste)

            // Limpiar y establecer fondo blanco en coordenadas CSS (no escaladas)
            ctx.clearRect(0, 0, rect.width, rect.height);
            ctx.fillStyle = '#fff';
            ctx.fillRect(0, 0, rect.width, rect.height);

            // Resetear estado
            isDrawing = false;
            hasSignature = false;

            // Limpiar input hidden
            const signatureDataInput = document.getElementById('signature_data');
            if (signatureDataInput) {
                signatureDataInput.value = '';
            }

            // Resetear contador de intentos
            setupTries = 0;
        }

        // ================================================================
        // 2.4 HANDLERS DE EVENTOS POINTER
        // ================================================================

        /**
         * Handler para pointerdown (iniciar dibujo)
         * @param {PointerEvent} ev - Evento pointer
         */
        function onDown(ev) {
            // Prevenir comportamientos por defecto (scroll, zoom, selección)
            ev.preventDefault();
            ev.stopPropagation();

            // Solo dibujar si estamos en modo manual y el canvas está listo
            const signMethodManual = document.getElementById('signMethodManual');
            if (signMethodManual && !signMethodManual.checked) {
                return; // No dibujar si está en modo generado
            }

            if (!ctx) {
                return; // Canvas no inicializado
            }

            // Capturar el pointer (CRÍTICO: mantiene el trazo aunque salga del canvas)
            try {
                canvas.setPointerCapture(ev.pointerId);
            } catch (e) {
                console.debug('TMS Portal Sign: Pointer capture no disponible:', e);
            }

            // Obtener coordenadas relativas al canvas
            const {x, y} = getPoint(ev);

            // Iniciar dibujo
            isDrawing = true;
            ctx.beginPath();
            ctx.moveTo(x, y);
        }

        /**
         * Handler para pointermove (dibujar mientras se mueve)
         * @param {PointerEvent} ev - Evento pointer
         */
        function onMove(ev) {
            // Solo dibujar si estamos en modo dibujo
            if (!isDrawing || !ctx) return;

            // Prevenir comportamientos por defecto
            ev.preventDefault();
            ev.stopPropagation();

            // Obtener coordenadas actuales
            const {x, y} = getPoint(ev);

            // Dibujar línea desde la última posición hasta la actual
            ctx.lineTo(x, y);
            ctx.stroke();

            // Marcar que hay firma dibujada
            hasSignature = true;
        }

        /**
         * Handler para pointerup y pointercancel (terminar dibujo)
         * @param {PointerEvent} ev - Evento pointer
         */
        function onUp(ev) {
            // Terminar dibujo
            if (isDrawing) {
                isDrawing = false;
                try {
                    ctx.closePath();
                } catch (e) {
                    console.debug('TMS Portal Sign: Error al cerrar path:', e);
                }
            }

            // Liberar pointer capture
            if (ev && ev.pointerId !== undefined) {
                try {
                    canvas.releasePointerCapture(ev.pointerId);
                } catch (e) {
                    console.debug('TMS Portal Sign: Error al liberar pointer capture:', e);
                }
            }

            // Prevenir comportamientos por defecto
            if (ev) {
                ev.preventDefault();
                ev.stopPropagation();
            }
        }

        // ================================================================
        // BIND DE EVENTOS (solo una vez usando dataset.bound)
        // ================================================================

        /**
         * Adjunta los event listeners al canvas solo una vez
         * CRÍTICO: Evita duplicación de listeners al abrir/cerrar el modal
         */
        function bindEventsOnce() {
            // Verificar si ya se bindearon los eventos (usando dataset)
            if (canvas.dataset.bound === '1') {
                return; // Ya están bindeados, no volver a hacerlo
            }

            // Adjuntar event listeners
            canvas.addEventListener('pointerdown', onDown);
            canvas.addEventListener('pointermove', onMove);
            canvas.addEventListener('pointerup', onUp);
            canvas.addEventListener('pointercancel', onUp);

            // Marcar que ya se bindearon
            canvas.dataset.bound = '1';
        }

        // ================================================================
        // 2.5 UI RADIOS (mostrar/ocultar botón generar)
        // ================================================================

        /**
         * Sincroniza la UI según el método de firma seleccionado
         * Muestra/oculta el botón "Generar Firma" y actualiza el hint
         */
        function syncRadioUI() {
            const signMethodManual = document.getElementById('signMethodManual');
            const signMethodGenerated = document.getElementById('signMethodGenerated');
            const generateBtn = document.getElementById('generateSignatureBtn');
            const hint = document.getElementById('signatureHint');

            if (!signMethodManual || !signMethodGenerated) {
                return;
            }

            // Verificar qué método está seleccionado
            if (signMethodGenerated.checked) {
                // Modo generado: mostrar botón "Generar Firma"
                if (generateBtn) {
                    generateBtn.style.display = '';
                }
                if (hint) {
                    hint.textContent = "Presione 'Generar Firma' para crear su firma con su nombre.";
                }
            } else {
                // Modo manual: ocultar botón "Generar Firma"
                if (generateBtn) {
                    generateBtn.style.display = 'none';
                }
                if (hint) {
                    hint.textContent = 'Dibuje su firma en el recuadro superior';
                }
            }
        }

        // Adjuntar listeners a los radios para sincronizar UI
        const signMethodManual = document.getElementById('signMethodManual');
        const signMethodGenerated = document.getElementById('signMethodGenerated');
        if (signMethodManual) {
            signMethodManual.addEventListener('change', syncRadioUI);
        }
        if (signMethodGenerated) {
            signMethodGenerated.addEventListener('change', syncRadioUI);
        }

        // ================================================================
        // 2.6 BOTÓN LIMPIAR
        // ================================================================

        /**
         * Limpia el canvas (dibuja fondo blanco)
         */
        function clearCanvas() {
            // Asegurar que setupCanvas() se ejecutó si ctx no está listo
            if (!ctx) {
                setupCanvas();
                if (!ctx) return; // Si aún no está listo, salir
            }

            // Obtener rect para dimensiones
            const rect = getRect();

            // Limpiar y dibujar fondo blanco (sin romper transform)
            ctx.clearRect(0, 0, rect.width, rect.height);
            ctx.fillStyle = '#fff';
            ctx.fillRect(0, 0, rect.width, rect.height);

            // Resetear estado
            hasSignature = false;
            isDrawing = false;

            // Limpiar input hidden
            const signatureDataInput = document.getElementById('signature_data');
            if (signatureDataInput) {
                signatureDataInput.value = '';
            }
        }

        // Adjuntar listener al botón "Limpiar Firma"
        const clearBtn = document.getElementById('clearSignature');
        if (clearBtn) {
            clearBtn.addEventListener('click', function(e) {
                e.preventDefault();
                clearCanvas();
            });
        }

        // ================================================================
        // 2.7 "GENERAR FIRMA" CON NOMBRE (debe dibujar sí o sí)
        // ================================================================

        /**
         * Genera una firma dibujando el nombre en letra cursiva centrada
         * CRÍTICO: Debe dibujar el texto sí o sí
         */
        function renderNameSignature() {
            // Leer nombre del input
            const nameInput = document.getElementById('signature_name');
            if (!nameInput) {
                alert('No se encontró el campo de nombre.');
                return;
            }

            const name = nameInput.value.trim();
            if (!name) {
                alert('Por favor, ingrese su nombre completo antes de generar la firma.');
                nameInput.focus();
                return;
            }

            // Asegurar que setupCanvas() se ejecutó (ctx listo y rect válido)
            if (!ctx) {
                setupCanvas();
                if (!ctx) {
                    alert('El canvas no está listo. Por favor, espere un momento e intente nuevamente.');
                    return;
                }
            }

            // Obtener rect para dimensiones
            const rect = getRect();

            // Limpiar fondo blanco
            ctx.clearRect(0, 0, rect.width, rect.height);
            ctx.fillStyle = '#fff';
            ctx.fillRect(0, 0, rect.width, rect.height);

            // Guardar estado del contexto
            ctx.save();

            // Tamaño de fuente inicial
            let fontSize = 54;

            // Configurar fuente cursiva con fallbacks
            // El navegador usará la primera fuente disponible
            const fontFamily = "'Segoe Script','Brush Script MT','Lucida Handwriting',cursive";
            ctx.font = fontSize + 'px ' + fontFamily;

            // Medir ancho del texto y ajustar tamaño si es muy largo
            let textWidth = ctx.measureText(name).width;
            const maxWidth = rect.width - 40; // Margen de 20px a cada lado

            // Reducir tamaño de fuente hasta que quepa
            while (textWidth > maxWidth && fontSize > 24) {
                fontSize -= 2;
                ctx.font = fontSize + 'px ' + fontFamily;
                textWidth = ctx.measureText(name).width;
            }

            // Aplicar leve inclinación (shear) para efecto cursiva más realista
            // Transformación: [1, shearY, shearX, 1, translateX, translateY]
            // -0.18 es una inclinación sutil hacia la derecha (cursiva natural)
            ctx.transform(1, 0, -0.18, 1, 0, 0);

            // Configurar estilo del texto
            ctx.fillStyle = '#111';           // Color negro (casi negro)
            ctx.textAlign = 'center';         // Texto centrado horizontalmente
            ctx.textBaseline = 'middle';      // Texto centrado verticalmente

            // Dibujar el texto centrado (con offset en X por la transformación)
            const centerX = (rect.width / 2) + 10; // Offset para compensar la inclinación
            const centerY = rect.height / 2;
            ctx.fillText(name, centerX, centerY);

            // Restaurar estado del contexto (quita la transformación)
            ctx.restore();

            // Marcar que hay firma generada
            hasSignature = true;
        }

        // Adjuntar listener al botón "Generar Firma"
        const generateBtn = document.getElementById('generateSignatureBtn');
        if (generateBtn) {
            generateBtn.addEventListener('click', function(e) {
                e.preventDefault();
                renderNameSignature();
            });
        }

        // ================================================================
        // 2.8 ANTES DEL SUBMIT: siempre guardar base64 en #signature_data
        // ================================================================

        /**
         * Intercepta el submit del formulario
         * Valida nombre y firma, y guarda base64 en #signature_data
         */
        if (signForm) {
            signForm.addEventListener('submit', function(e) {
                // Validar nombre
                const nameInput = document.getElementById('signature_name');
                if (nameInput && !nameInput.value.trim()) {
                    e.preventDefault();
                    alert('Por favor, ingrese su nombre completo.');
                    nameInput.focus();
                    return false;
                }

                // Validar que haya firma (dibujada o generada)
                if (!hasSignature) {
                    e.preventDefault();
                    alert('Por favor, dibuje su firma o genere una firma con su nombre antes de continuar.');
                    return false;
                }

                // Validar que el canvas esté inicializado
                if (!ctx) {
                    e.preventDefault();
                    alert('El canvas no está inicializado. Por favor, recargue la página e intente nuevamente.');
                    return false;
                }

                // Convertir canvas a base64 PNG
                // toDataURL() retorna "data:image/png;base64,iVBORw0KG..."
                const base64Data = canvas.toDataURL('image/png');

                // Guardar en el input hidden #signature_data
                const signatureDataInput = document.getElementById('signature_data');
                if (signatureDataInput) {
                    signatureDataInput.value = base64Data;
                } else {
                    console.error('TMS Portal Sign: No se encontró el input #signature_data');
                    e.preventDefault();
                    return false;
                }

                // Permitir que el formulario se envíe normalmente
                return true;
            });
        }

        // ================================================================
        // 3. BOOTSTRAP MODAL: inicializar cuando se muestre (causa raíz)
        // ================================================================

        /**
         * EVENTO: Modal se muestra (shown.bs.modal)
         * CRÍTICO: El canvas se mide bien SOLO cuando el modal ya está visible
         */
        modalEl.addEventListener('shown.bs.modal', function() {
            // Resetear contador de intentos
            setupTries = 0;

            // Configurar canvas (con reintentos si es necesario)
            setupCanvas();

            // Bindear eventos (solo una vez)
            bindEventsOnce();

            // Sincronizar UI de radios
            syncRadioUI();
        });

        /**
         * EVENTO: Modal se oculta (hidden.bs.modal)
         * Resetear estado de dibujo
         */
        modalEl.addEventListener('hidden.bs.modal', function() {
            isDrawing = false;
        });

        return this._super.apply(this, arguments);
    },
});
