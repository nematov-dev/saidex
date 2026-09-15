(function () {
    "use strict";

    function initSidebarToggle() {
        var btn = document.querySelector("[data-sidebar-toggle]");
        if (!btn) return;
        btn.addEventListener("click", function () {
            var collapsed = document.documentElement.getAttribute("data-sidebar-collapsed") === "1";
            var next = collapsed ? "0" : "1";
            document.documentElement.setAttribute("data-sidebar-collapsed", next);
            try { localStorage.setItem("saidex_sidebar_collapsed", next); } catch (e) { /* noop */ }
        });
    }

    function initMobileMenu() {
        var openBtn = document.querySelector("[data-mobile-menu-toggle]");
        if (!openBtn) return;

        var backdrop = document.querySelector(".sidebar-backdrop");
        if (!backdrop) {
            backdrop = document.createElement("div");
            backdrop.className = "sidebar-backdrop";
            document.body.appendChild(backdrop);
        }

        function closeMenu() {
            document.documentElement.removeAttribute("data-sidebar-open");
        }
        function toggleMenu() {
            var isOpen = document.documentElement.getAttribute("data-sidebar-open") === "1";
            document.documentElement.setAttribute("data-sidebar-open", isOpen ? "0" : "1");
        }

        openBtn.addEventListener("click", toggleMenu);
        backdrop.addEventListener("click", closeMenu);
        // Sidebardagi havolani bosganda menyu avtomatik yopilsin (mobil UX).
        document.querySelectorAll(".sidebar a").forEach(function (link) {
            link.addEventListener("click", closeMenu);
        });
    }

    function initThemeToggle() {
        var btn = document.querySelector("[data-theme-toggle]");
        if (!btn) return;

        function updateIcon() {
            var theme = document.documentElement.getAttribute("data-bs-theme") || "light";
            var icon = btn.querySelector("i");
            if (icon) icon.className = theme === "dark" ? "bi bi-sun" : "bi bi-moon-stars";
        }

        updateIcon();
        btn.addEventListener("click", function () {
            var current = document.documentElement.getAttribute("data-bs-theme") || "light";
            var next = current === "dark" ? "light" : "dark";
            document.documentElement.setAttribute("data-bs-theme", next);
            try { localStorage.setItem("saidex_theme", next); } catch (e) { /* noop */ }
            updateIcon();
        });
    }

    function initConfirmModals() {
        // Barcha "xavfli" formalar (o'chirish, chiqish va h.k.) endi brauzerning
        // o'ziga xos confirm() oynasi o'rniga saytning o'z uslubidagi (qizil/yashil
        // tugmali) modali orqali tasdiqlanadi. Forma <form data-confirm="xabar">
        // atributiga ega bo'lsa, shu modal ishga tushadi.
        document.addEventListener("submit", function (e) {
            var form = e.target;
            if (!(form instanceof HTMLFormElement) || !form.hasAttribute("data-confirm")) return;
            if (form.dataset.confirmed === "1") return;

            var modalEl = document.getElementById("confirmActionModal");
            if (!modalEl || typeof bootstrap === "undefined") return; // fallback: oddiy submit davom etadi

            e.preventDefault();
            document.getElementById("confirmActionMessage").textContent = form.getAttribute("data-confirm");
            var modal = bootstrap.Modal.getOrCreateInstance(modalEl);
            var yesBtn = document.getElementById("confirmActionYesBtn");

            function onYes() {
                yesBtn.removeEventListener("click", onYes);
                modal.hide();
                form.dataset.confirmed = "1";
                form.submit();
            }
            yesBtn.addEventListener("click", onYes);
            modal.show();
        }, true);
    }

    function initBulkSelect() {
        // Arizalar/Arxiv jadvalidagi "hammasini tanlash" katakchasi va shu
        // asosda "Tanlanganlarni o'chirish" tugmasini yoq/o'chir qiladi.
        // Boshqa sahifalarda bu elementlar yo'q bo'lgani uchun jim chiqib ketadi.
        var selectAll = document.getElementById("selectAllLeads");
        var bulkBtn = document.getElementById("bulkDeleteBtn");
        var checkboxes = document.querySelectorAll(".lead-select");
        if (!selectAll || !bulkBtn || !checkboxes.length) return;

        function updateBulkBtn() {
            var anyChecked = Array.prototype.some.call(checkboxes, function (cb) { return cb.checked; });
            bulkBtn.disabled = !anyChecked;
        }
        selectAll.addEventListener("change", function () {
            checkboxes.forEach(function (cb) { cb.checked = selectAll.checked; });
            updateBulkBtn();
        });
        checkboxes.forEach(function (cb) {
            cb.addEventListener("change", function () {
                if (!cb.checked) selectAll.checked = false;
                updateBulkBtn();
            });
        });
        updateBulkBtn();
    }

    document.addEventListener("DOMContentLoaded", function () {
        initSidebarToggle();
        initMobileMenu();
        initThemeToggle();
        initConfirmModals();
        initBulkSelect();
    });
})();
