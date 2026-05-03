
/* Backend API override layer: keeps existing UI, replaces localStorage workflows */
(function(){
    const ASSET_BASE = new URL("./images/", window.location.href);
    function assetUrl(fileName){
        return new URL(fileName, ASSET_BASE).href;
    }

    function setImageWithFallback(elementId, fileName){
        const img = document.getElementById(elementId);
        if(!img){ return; }
        img.onerror = function(){
            this.onerror = null;
            this.src = assetUrl("logo.png");
        };
        img.src = assetUrl(fileName);
    }

    function setupTherapyStaticImages(){
        setImageWithFallback("vamanaStaticImg", "Vamana_therapy.jpg");
        setImageWithFallback("virechanaStaticImg", "Virechana_therapy.jpg");
        setImageWithFallback("bastiStaticImg", "Basti_Therapy.jpg");
        setImageWithFallback("nasyaStaticImg", "Nasya_therapy.jpg");
        setImageWithFallback("raktamokshanaStaticImg", "Raktamokshana_therapy.jpg");
    }

    const API_BASE = (() => {
        const saved = localStorage.getItem("ep_api_base");
        if(saved){ return saved; }
        if(window.location.protocol === "file:"){ return "http://127.0.0.1:5000"; }
        const host = window.location.hostname || "127.0.0.1";
        if(host === "localhost" || host === "127.0.0.1"){ return "http://127.0.0.1:5000"; }
        return window.location.protocol + "//" + host + ":5000";
    })();
    let backendWarningShown = false;
    const state = {
        patientToken: localStorage.getItem("ep_patient_token") || "",
        doctorToken: localStorage.getItem("ep_doctor_token") || "",
        patient: JSON.parse(localStorage.getItem("ep_patient_profile") || "null"),
        doctor: JSON.parse(localStorage.getItem("ep_doctor_profile") || "null"),
        analysis: JSON.parse(localStorage.getItem("ep_last_analysis") || "null"),
        progress: localStorage.getItem("ep_progress") || "Not Started"
    };

    function persist(){
        if(state.patientToken){ localStorage.setItem("ep_patient_token", state.patientToken); } else { localStorage.removeItem("ep_patient_token"); }
        if(state.doctorToken){ localStorage.setItem("ep_doctor_token", state.doctorToken); } else { localStorage.removeItem("ep_doctor_token"); }
        if(state.patient){ localStorage.setItem("ep_patient_profile", JSON.stringify(state.patient)); } else { localStorage.removeItem("ep_patient_profile"); }
        if(state.doctor){ localStorage.setItem("ep_doctor_profile", JSON.stringify(state.doctor)); } else { localStorage.removeItem("ep_doctor_profile"); }
        if(state.analysis){ localStorage.setItem("ep_last_analysis", JSON.stringify(state.analysis)); } else { localStorage.removeItem("ep_last_analysis"); }
        localStorage.setItem("ep_progress", state.progress || "Not Started");
    }

    async function api(path, method="GET", body=null, authType=""){
        const headers = {"Content-Type":"application/json"};
        const token = authType === "doctor" ? state.doctorToken : state.patientToken;
        if(authType && token){ headers.Authorization = "Bearer " + token; }
        let res;
        try{
            res = await fetch(API_BASE + path, {
                method:method,
                headers:headers,
                body:body ? JSON.stringify(body) : undefined
            });
        }catch(error){
            throw new Error("Cannot reach backend at " + API_BASE + ". Start backend using: python app.py");
        }
        let data = {};
        try{ data = await res.json(); }catch(error){}
        if(!res.ok){ throw new Error(data.error || data.message || ("Request failed: " + res.status)); }
        return data;
    }

    async function checkBackendHealth(){
        try{
            const res = await fetch(API_BASE + "/health", {method:"GET"});
            if(!res.ok){
                throw new Error("Health check failed");
            }
            updateGoogleStatus("Backend connected. Register/login is ready.");
        }catch(error){
            if(!backendWarningShown){
                backendWarningShown = true;
                showAIPopup("Backend API not running at " + API_BASE + ". Start it with: python app.py","warning");
            }
            updateGoogleStatus("Backend is offline. Start backend with: python app.py");
        }
    }

    function checkedSymptoms(name){
        return Array.from(document.querySelectorAll('input[name="' + name + '"]:checked'))
        .map((el)=>el.parentElement ? el.parentElement.textContent.trim() : (el.value || ""));
    }

    function therapyImage(therapy){
        if((therapy || "").includes("Basti")) return assetUrl("Basti_Therapy.jpg");
        if((therapy || "").includes("Virechana")) return assetUrl("Virechana_therapy.jpg");
        if((therapy || "").includes("Vamana")) return assetUrl("Vamana_therapy.jpg");
        return assetUrl("logo.png");
    }

    async function refreshDoctorHint(){
        const hint = document.getElementById("doctorEmailHint");
        if(!hint){ return; }
        try{
            const doctors = await api("/api/doctors");
            hint.innerText = doctors.length ? doctors.map((d)=>d.email).join(", ") : "No doctor registered yet";
        }catch(error){
            hint.innerText = "Unable to load doctors";
        }
    }

    window.showLogin = function(){
        document.getElementById("loginForm").style.display="block";
        document.getElementById("registerForm").style.display="none";
        updateGoogleStatus("Backend API mode active. Google login is enabled through backend.");
    };

    window.showRegister = function(){
        document.getElementById("loginForm").style.display="none";
        document.getElementById("registerForm").style.display="block";
    };

    async function finishGoogleBackendLogin(result){
        let googleIdToken = "";
        if(result && result.credential && result.credential.idToken){
            googleIdToken = result.credential.idToken;
        }
        if(!googleIdToken && result && result.user && result.user.getIdToken){
            googleIdToken = await result.user.getIdToken();
        }
        if(!googleIdToken){
            throw new Error("Unable to retrieve Google ID token");
        }
        const data = await api("/api/auth/google","POST",{id_token:googleIdToken});
        state.patientToken = data.session.token;
        state.patient = data.patient;
        state.analysis = null;
        state.progress = "Not Started";
        localStorage.setItem("patientName", data.patient.name || "");
        localStorage.setItem("email", data.patient.email || "");
        localStorage.setItem("age", String(data.patient.age || ""));
        persist();
        updateGoogleStatus("Google login successful via backend.");
        showAIPopup("Google login successful","success");
        showPage("dashboardPage");
    }

    async function handleGoogleRedirectResult(){
        if(!(window.firebase && firebase.apps && firebase.apps.length)){ return; }
        try{
            const result = await firebase.auth().getRedirectResult();
            if(result && result.user){
                await finishGoogleBackendLogin(result);
            }
        }catch(error){
            updateGoogleStatus(error.message || "Google redirect login failed.");
            showAIPopup(error.message || "Google redirect login failed","error");
        }
    }

    window.signInWithGoogle = async function(){
        if(!(window.location.protocol === "http:" || window.location.protocol === "https:")){
            const msg = "Open this app via http://localhost (not file://). Run: python -m http.server 5500";
            updateGoogleStatus(msg);
            showAIPopup(msg,"error");
            return;
        }
        if(!(window.firebase && firebase.apps && firebase.apps.length)){
            updateGoogleStatus("Firebase config missing. Add valid Firebase config to use Google login.");
            showAIPopup("Google login setup incomplete: Firebase config missing.","error");
            return;
        }
        setButtonState("googleLoginBtn", true, "Connecting...");
        try{
            const provider = new firebase.auth.GoogleAuthProvider();
            provider.setCustomParameters({ prompt:"select_account" });
            const result = await firebase.auth().signInWithPopup(provider);
            await finishGoogleBackendLogin(result);
        }catch(error){
            if(error && (error.code === "auth/popup-blocked" || error.code === "auth/popup-closed-by-user")){
                try{
                    const provider = new firebase.auth.GoogleAuthProvider();
                    provider.setCustomParameters({ prompt:"select_account" });
                    updateGoogleStatus("Popup blocked. Redirecting to Google sign-in...");
                    showAIPopup("Popup blocked. Continuing with redirect sign-in.","warning");
                    await firebase.auth().signInWithRedirect(provider);
                    return;
                }catch(redirectError){
                    updateGoogleStatus(redirectError.message || "Google redirect login failed.");
                    showAIPopup(redirectError.message || "Google redirect login failed","error");
                    return;
                }
            }
            updateGoogleStatus(error.message || "Google login failed.");
            showAIPopup(error.message || "Google login failed","error");
        }finally{
            setButtonState("googleLoginBtn", false, "Continue with Google");
        }
    };

    window.resetDoctorLoginForm = async function(){
        document.getElementById("doctorLoginForm").style.display = "block";
        document.getElementById("doctorRegisterForm").style.display = "none";
        await refreshDoctorHint();
    };

    window.register = async function(){
        const terms=document.getElementById("termsCheck").checked;
        const name=document.getElementById("nameInput").value.trim();
        const email=normalizeEmail(document.getElementById("emailInput").value);
        const age=document.getElementById("ageInput").value.trim();
        const password=document.getElementById("passwordInput").value;
        if(!terms){ showAIPopup("Please accept Terms & Conditions","error"); return; }
        if(name==="" || email==="" || age==="" || password===""){ showAIPopup("Please fill all fields","error"); return; }
        if(!isValidEmail(email)){ showAIPopup("Enter a valid email address","error"); return; }
        if(isNaN(age) || Number(age) <= 0){ showAIPopup("Enter a valid age","error"); return; }
        if(password.length < 6){ showAIPopup("Password must be at least 6 characters","error"); return; }
        try{
            const data = await api("/api/auth/patient/register","POST",{name:name,email:email,age:Number(age),password:password});
            state.patientToken = data.session.token;
            state.patient = {id:data.session.user_id,name:name,email:email,age:Number(age)};
            state.analysis = null;
            state.progress = "Not Started";
            localStorage.setItem("patientName", name);
            localStorage.setItem("email", email);
            localStorage.setItem("age", String(age));
            persist();
            showAIPopup("Registration successful","success");
            showPage("dashboardPage");
        }catch(error){
            showAIPopup(error.message,"error");
        }
    };

    window.login = async function(){
        const name = document.getElementById("loginName").value.trim();
        const email = normalizeEmail(document.getElementById("loginEmail").value);
        const password = document.getElementById("loginPassword").value;
        if(name==="" || email==="" || password===""){ showAIPopup("Enter name, email, and password","error"); return; }
        if(!isValidEmail(email)){ showAIPopup("Enter a valid email address","error"); return; }
        try{
            const data = await api("/api/auth/patient/login","POST",{email:email,password:password});
            if((data.patient.name || "").trim().toLowerCase() !== name.toLowerCase()){
                showAIPopup("Name does not match this email","error");
                return;
            }
            state.patientToken = data.session.token;
            state.patient = data.patient;
            localStorage.setItem("patientName", data.patient.name || "");
            localStorage.setItem("email", data.patient.email || "");
            localStorage.setItem("age", String(data.patient.age || ""));
            persist();
            showAIPopup("Login successful","success");
            showPage("dashboardPage");
        }catch(error){
            showAIPopup(error.message,"error");
        }
    };

    window.registerDoctor = async function(){
        const name = document.getElementById("doctorNameInput").value.trim();
        const email = normalizeEmail(document.getElementById("doctorEmailInput").value);
        const hospital = document.getElementById("doctorHospitalInput").value.trim();
        const specialty = document.getElementById("doctorSpecialtyInput").value;
        const password = document.getElementById("doctorPasswordInput").value;
        if(name==="" || email==="" || hospital==="" || specialty==="" || password===""){ showAIPopup("Enter doctor name, email, hospital, specialty, and password","error"); return; }
        if(!isValidEmail(email)){ showAIPopup("Enter a valid doctor email address","error"); return; }
        if(password.length < 6){ showAIPopup("Doctor password must be at least 6 characters","error"); return; }
        try{
            await api("/api/auth/doctor/register","POST",{name:name,email:email,hospital:hospital,specialty:specialty,password:password});
            showAIPopup("Doctor registered successfully","success");
            document.getElementById("doctorNameInput").value = "";
            document.getElementById("doctorEmailInput").value = "";
            document.getElementById("doctorHospitalInput").value = "";
            document.getElementById("doctorSpecialtyInput").value = "";
            document.getElementById("doctorPasswordInput").value = "";
            document.getElementById("doctorEmail").value = email;
            showDoctorLoginForm();
            await refreshDoctorHint();
        }catch(error){
            showAIPopup(error.message,"error");
        }
    };

    window.doctorLogin = async function(){
        const email = normalizeEmail(document.getElementById("doctorEmail").value);
        const password = document.getElementById("doctorPassword").value;
        if(email==="" || password===""){ showAIPopup("Enter doctor email and password","error"); return; }
        if(!isValidEmail(email)){ showAIPopup("Enter a valid doctor email address","error"); return; }
        try{
            const data = await api("/api/auth/doctor/login","POST",{email:email,password:password});
            state.doctorToken = data.session.token;
            state.doctor = data.doctor;
            localStorage.setItem("doctorLoggedIn","true");
            localStorage.setItem("doctorName", data.doctor.name || "");
            localStorage.setItem("doctorEmail", data.doctor.email || "");
            localStorage.setItem("doctorSpecialty", data.doctor.specialty || "General Panchakarma");
            persist();
            showAIPopup("Doctor login successful","success");
            showPage("doctorPage");
        }catch(error){
            showAIPopup(error.message,"error");
        }
    };

    window.logout = async function(){
        try{ await api("/api/auth/logout","POST",null,"patient"); }catch(error){}
        state.patientToken = "";
        state.patient = null;
        state.analysis = null;
        state.progress = "Not Started";
        localStorage.removeItem("patientName");
        localStorage.removeItem("email");
        localStorage.removeItem("age");
        persist();
        showPage("loginPage");
    };

    window.doctorLogout = async function(){
        try{ await api("/api/auth/logout","POST",null,"doctor"); }catch(error){}
        state.doctorToken = "";
        state.doctor = null;
        localStorage.removeItem("doctorLoggedIn");
        localStorage.removeItem("doctorName");
        localStorage.removeItem("doctorEmail");
        localStorage.removeItem("doctorSpecialty");
        persist();
        showPage("loginPage");
    };

    window.analyze = async function(){
        if(!state.patientToken){
            showAIPopup("Please login first","error");
            showPage("loginPage");
            return;
        }
        document.getElementById("loader").style.display="block";
        try{
            const data = await api("/api/analysis","POST",{
                vata_symptoms: checkedSymptoms("vata"),
                pitta_symptoms: checkedSymptoms("pitta"),
                kapha_symptoms: checkedSymptoms("kapha")
            },"patient");
            state.analysis = data.result;
            state.progress = "Not Started";
            persist();
            showPage("resultPage");
        }
        catch(error){
            showAIPopup(error.message,"error");
        }
        finally{
            document.getElementById("loader").style.display="none";
        }
    };

    window.loadResult = async function(){
        if(!state.analysis && state.patientToken){
            try{
                const latest = await api("/api/analysis/latest","GET",null,"patient");
                if(latest && latest.final_dosha){
                    state.analysis = {
                        vata_count: latest.vata_count || 0,
                        pitta_count: latest.pitta_count || 0,
                        kapha_count: latest.kapha_count || 0,
                        final_dosha: latest.final_dosha,
                        therapy: latest.therapy || "",
                        diet: latest.diet || "",
                        therapy_description: latest.therapy_description || ""
                    };
                    persist();
                }
            }catch(error){}
        }
        const r = state.analysis || {
            final_dosha:"Not analyzed",
            therapy:"Complete the symptom analysis to see recommendations",
            diet:"Balanced routine and light meals",
            therapy_description:"Your therapy recommendation will appear after the analysis step.",
            vata_count:0,pitta_count:0,kapha_count:0
        };
        document.getElementById("doshaText").innerText = r.final_dosha;
        document.getElementById("therapyText").innerText = r.therapy;
        document.getElementById("dietText").innerText = r.diet;
        document.getElementById("therapyDescription").innerText = r.therapy_description;
        document.getElementById("therapyImage").src = therapyImage(r.therapy);
        document.getElementById("progressText").innerText = state.progress || "Not Started";
        if(doshaChart){ doshaChart.destroy(); }
        doshaChart = new Chart(document.getElementById("chartCanvas"),{
            type:"pie",
            data:{ labels:["Vata","Pitta","Kapha"], datasets:[{ data:[r.vata_count || 0,r.pitta_count || 0,r.kapha_count || 0], backgroundColor:["#43a047","#ef5350","#42a5f5"] }] }
        });
    };

    window.completeTreatment = function(){
        state.progress = "Completed";
        persist();
        loadResult();
    };

    window.downloadPDF = function(){
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF();
        const r = state.analysis || {};
        doc.text("E-Panchakarma Report",20,20);
        doc.text("Patient: " + ((state.patient && state.patient.name) || "N/A"),20,40);
        doc.text("Dosha: " + (r.final_dosha || "N/A"),20,50);
        doc.text("Therapy: " + (r.therapy || "N/A"),20,60);
        doc.save("E-Panchakarma-Report.pdf");
    };

    window.updateDoctorRecommendation = async function(){
        const issue = document.getElementById("patientIssue") ? document.getElementById("patientIssue").value : "";
        const select = document.getElementById("doctorSelect");
        const suggestedDoctorName = document.getElementById("suggestedDoctorName");
        const suggestedDoctorReason = document.getElementById("suggestedDoctorReason");
        const doctorMatchList = document.getElementById("doctorMatchList");
        const manualDoctorHint = document.getElementById("manualDoctorHint");
        if(!select){ return; }
        select.innerHTML = "";
        if(doctorMatchList){ doctorMatchList.innerHTML = ""; }
        const dosha = state.analysis ? (state.analysis.final_dosha || "") : "";
        const therapy = state.analysis ? (state.analysis.therapy || "") : "";

        try{
            const rec = await api("/api/doctors/recommend?issue=" + encodeURIComponent(issue) + "&dosha=" + encodeURIComponent(dosha) + "&therapy=" + encodeURIComponent(therapy));
            const top = rec.top_matches || [];
            if(top.length === 0){
                const opt = document.createElement("option");
                opt.value = "";
                opt.textContent = "No doctor registered yet";
                select.appendChild(opt);
                suggestedDoctorName.innerText = "No doctor available";
                suggestedDoctorReason.innerText = "Register doctor profiles first.";
                if(manualDoctorHint){ manualDoctorHint.innerText = "Doctor selection will appear after doctor registration."; }
                return;
            }
            const placeholder = document.createElement("option");
            placeholder.value = "";
            placeholder.textContent = "Select doctor manually";
            select.appendChild(placeholder);
            top.forEach((d,index)=>{
                const opt = document.createElement("option");
                opt.value = String(d.id);
                opt.textContent = d.name + " - " + (d.specialty || "General Panchakarma") + " (Score " + d.score + ")";
                if(index === 0){ opt.selected = true; }
                select.appendChild(opt);
            });
            const best = rec.recommended_doctor;
            suggestedDoctorName.innerText = best ? (best.name + " (" + best.specialty + ")") : "No doctor suggested yet";
            suggestedDoctorReason.innerText = best ? best.reason : "Choose issue to get recommendation.";
            if(manualDoctorHint){ manualDoctorHint.innerText = "System preselected the best doctor. You can still choose another doctor."; }
            if(doctorMatchList){
                top.forEach((d,index)=>{
                    const li = document.createElement("li");
                    li.innerText = (index + 1) + ". Dr. " + d.name + " (" + d.specialty + ") - " + d.reason;
                    doctorMatchList.appendChild(li);
                });
            }
        }catch(error){
            showAIPopup(error.message,"error");
        }
    };

    window.bookAppointment = async function(){
        if(!state.patientToken){
            showAIPopup("Please login first","error");
            return;
        }
        const date=document.getElementById("appointDate").value;
        const time=document.getElementById("appointTime").value;
        const issue=document.getElementById("patientIssue").value;
        const doctorIdValue=document.getElementById("doctorSelect").value;
        if(issue==="" ){ showAIPopup("Please choose health issue","error"); return; }
        if(date==="" || time===""){ showAIPopup("Please select date and time","error"); return; }
        const payload = {issue:issue, appointment_date:date, appointment_time:time};
        if(doctorIdValue){ payload.doctor_id = Number(doctorIdValue); } else { payload.use_system_suggestion = true; }
        try{
            await api("/api/appointments","POST",payload,"patient");
            await updatePatientStatus();
            showAIPopup("Appointment booked","success");
        }catch(error){
            showAIPopup(error.message,"error");
        }
    };

    window.updatePatientStatus = async function(){
        const statusEl = document.getElementById("appointStatus");
        if(!state.patientToken){
            statusEl.innerText = "Please login to view appointment status";
            return;
        }
        try{
            const list = await api("/api/appointments/my","GET",null,"patient");
            const latest = list.length ? list[0] : null;
            statusEl.innerText = latest ? (latest.status + " with Dr. " + (latest.doctor_name || "Assigned Doctor")) : "No appointment booked";
        }catch(error){
            statusEl.innerText = "Unable to load appointment status";
        }
    };

    window.loadAppointments = async function(){
        const listEl=document.getElementById("appointmentList");
        listEl.innerHTML="";
        try{
            const list=await api("/api/doctor/appointments","GET",null,"doctor");
            const latest = list.length ? list[0] : null;
            document.getElementById("docPatient").innerText = latest ? latest.patient_name : "Not available";
            document.getElementById("docDosha").innerText = latest ? (latest.dosha || "Not analyzed") : "Not analyzed";
            document.getElementById("docTherapy").innerText = latest ? (latest.therapy || "Not assigned") : "Not assigned";
            document.getElementById("docProgress").innerText = latest ? (latest.progress || "Not Started") : "Not Started";
            if(!list.length){
                const item=document.createElement("li");
                item.className="list-group-item";
                item.innerText="No appointments for this doctor yet.";
                listEl.appendChild(item);
                return;
            }
            list.forEach((a)=>{
                const item=document.createElement("li");
                item.className="list-group-item";
                item.innerHTML =
                "<b>" + (a.patient_name || "Patient") + "</b><br>" +
                "Issue: " + (a.issue || "General consultation") + "<br>" +
                "Booked via: " + (a.suggested_by_system ? "System suggestion" : "Manual doctor choice") + "<br>" +
                "Date: " + a.appointment_date + " | Time: " + a.appointment_time + "<br>" +
                "Status: <b>" + (a.status || "Pending") + "</b>";
                listEl.appendChild(item);
            });
        }
        catch(error){
            const item=document.createElement("li");
            item.className="list-group-item";
            item.innerText="Unable to load appointments.";
            listEl.appendChild(item);
        }
    };

    const originalShowPage = window.showPage;
    window.showPage = function(page, addToHistory=true){
        originalShowPage(page, addToHistory);
        if(page==="dashboardPage"){
            document.getElementById("patientName").innerText = (state.patient && state.patient.name) ? state.patient.name : "Patient";
        }
        if(page==="appointmentPage"){
            updatePatientStatus();
            updateDoctorRecommendation();
        }
        if(page==="doctorLoginPage"){
            resetDoctorLoginForm();
        }
        if(page==="doctorPage"){
            if(!state.doctorToken){
                showAIPopup("Access denied. Doctor login required.","error");
                originalShowPage("doctorLoginPage");
                return;
            }
            document.getElementById("doctorDisplayName").innerText = (state.doctor && state.doctor.name) ? state.doctor.name : "Doctor";
            document.getElementById("doctorDisplaySpecialty").innerText = (state.doctor && state.doctor.specialty) ? state.doctor.specialty : "Not assigned";
            loadAppointments();
        }
    };

    checkBackendHealth();
    setupTherapyStaticImages();
    handleGoogleRedirectResult();
    showLogin();
    if(state.patientToken && state.patient){
        showPage("dashboardPage", false);
    }
    else{
        showPage("loginPage", false);
    }
})();
