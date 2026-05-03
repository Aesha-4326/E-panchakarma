
if(!localStorage.getItem("doctorProfiles")){
    localStorage.setItem("doctorProfiles", "[]");
}
try{
    const existingDoctorProfiles = JSON.parse(localStorage.getItem("doctorProfiles") || "[]");
    const noProfiles = Array.isArray(existingDoctorProfiles) && existingDoctorProfiles.length === 0;
    if(noProfiles){
        localStorage.setItem("doctorProfiles", "[]");
    }
}catch(error){
}

let doshaChart = null;

function openTerms(){
    document.getElementById("termsModal").style.display="flex";
}

function closeTerms(){
    document.getElementById("termsModal").style.display="none";
}

function showAIPopup(message,type="success"){
    const popup=document.getElementById("aiPopup");
    const msg=document.getElementById("aiMessage");
    msg.innerText="AI: " + message;
    popup.className="ai-popup show " + type;

    setTimeout(()=>{
        popup.classList.remove("show");
    },3000);
}

function normalizeEmail(value){
    return value.trim().toLowerCase();
}

function isValidEmail(value){
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function togglePasswordVisibility(fieldId, isVisible){
    const input = document.getElementById(fieldId);
    if(!input){
        return;
    }
    input.type = isVisible ? "text" : "password";
}

function getDoctorProfiles(){
    try{
        const profiles = JSON.parse(localStorage.getItem("doctorProfiles") || "[]");
        return Array.isArray(profiles) ? profiles : [];
    }catch(error){
        return [];
    }
}

function saveDoctorProfiles(profiles){
    localStorage.setItem("doctorProfiles", JSON.stringify(profiles));
}

function getDoctorMatchMeta(profile, issue, dosha, therapy){
    const specialty = profile.specialty || "General Panchakarma";
    let score = specialty === "General Panchakarma" ? 1 : 0;
    let reason = "General Panchakarma support";

    const issueMap = {
        respiratory:{specialty:"Respiratory & Kapha Care", reason:"best fit for respiratory and Kapha complaints"},
        digestive:{specialty:"Digestive & Pitta Care", reason:"best fit for digestion and Pitta-related complaints"},
        joint:{specialty:"Vata & Pain Care", reason:"best fit for joint pain and Vata imbalance"},
        sinus:{specialty:"ENT & Head Care", reason:"best fit for sinus, headache, and head-region complaints"},
        skin:{specialty:"Skin & Blood Purification", reason:"best fit for skin-related conditions"},
        blood:{specialty:"Skin & Blood Purification", reason:"best fit for blood purification concerns"},
        general:{specialty:"General Panchakarma", reason:"good for general Panchakarma guidance"}
    };

    const mappedIssue = issueMap[issue];
    if(mappedIssue && specialty === mappedIssue.specialty){
        score += 4;
        reason = mappedIssue.reason;
    }

    if(dosha === "Kapha" && specialty === "Respiratory & Kapha Care"){
        score += 3;
        reason = "matches Kapha imbalance and respiratory cleansing needs";
    }
    if(dosha === "Pitta" && specialty === "Digestive & Pitta Care"){
        score += 3;
        reason = "matches Pitta imbalance and digestive detox needs";
    }
    if(dosha === "Vata" && specialty === "Vata & Pain Care"){
        score += 3;
        reason = "matches Vata imbalance and pain management needs";
    }

    if(therapy.includes("Nasya") && specialty === "ENT & Head Care"){
        score += 3;
        reason = "matches Nasya-related ENT and head care";
    }
    if(therapy.includes("Rakta") && specialty === "Skin & Blood Purification"){
        score += 3;
        reason = "matches blood purification and skin care";
    }
    if(therapy.includes("Vamana") && specialty === "Respiratory & Kapha Care"){
        score += 3;
        reason = "matches Vamana support for Kapha and respiratory detox";
    }
    if(therapy.includes("Virechana") && specialty === "Digestive & Pitta Care"){
        score += 3;
        reason = "matches Virechana support for digestive and Pitta detox";
    }
    if(therapy.includes("Basti") && specialty === "Vata & Pain Care"){
        score += 3;
        reason = "matches Basti support for Vata and pain management";
    }

    return {score:score, reason:reason};
}

function getRecommendedDoctor(issue){
    const ranked = getRankedDoctors(issue);
    return ranked[0] || null;
}

function getRankedDoctors(issue){
    const profiles = getDoctorProfiles();
    if(profiles.length === 0){
        return [];
    }
    const dosha = localStorage.getItem("finalDosha") || "";
    const therapy = localStorage.getItem("therapy") || "";
    return profiles
    .map((profile)=>{
        const match = getDoctorMatchMeta(profile, issue, dosha, therapy);
        return {
            profile:profile,
            score:match.score,
            reason:match.reason
        };
    })
    .sort((a,b)=>b.score - a.score || a.profile.name.localeCompare(b.profile.name));
}

function updateDoctorRecommendation(){  
    const issue = document.getElementById("patientIssue") ? document.getElementById("patientIssue").value : "";
    const select = document.getElementById("doctorSelect");
    const suggestedDoctorName = document.getElementById("suggestedDoctorName");
    const suggestedDoctorReason = document.getElementById("suggestedDoctorReason");
    const doctorMatchList = document.getElementById("doctorMatchList");
    const manualDoctorHint = document.getElementById("manualDoctorHint");
    const profiles = getDoctorProfiles();

    if(!select){
        return;
    }

    select.innerHTML = "";
    if(doctorMatchList){
        doctorMatchList.innerHTML = "";
    }

    if(profiles.length === 0){
        const option = document.createElement("option");
        option.value = "";
        option.textContent = "No doctor registered yet";
        select.appendChild(option);
        suggestedDoctorName.innerText = "No doctor available";
        suggestedDoctorReason.innerText = "Register one or more doctor profiles first.";
        if(manualDoctorHint){
            manualDoctorHint.innerText = "Doctor selection will appear after doctor registration.";
        }
        if(doctorMatchList){
            const empty = document.createElement("li");
            empty.innerText = "No doctor profiles available.";
            doctorMatchList.appendChild(empty);
        }
        return;
    }

    const rankedDoctors = getRankedDoctors(issue);
    const recommendation = rankedDoctors[0] || null;

    const placeholderOption = document.createElement("option");
    placeholderOption.value = "";
    placeholderOption.textContent = "Select doctor manually";
    select.appendChild(placeholderOption);

    rankedDoctors.forEach((rankedItem)=>{
        const profile = rankedItem.profile;
        const option = document.createElement("option");
        option.value = profile.email;
        option.textContent = profile.name + " - " + (profile.specialty || "General Panchakarma") + " (Score " + rankedItem.score + ")";
        if(recommendation && profile.email === recommendation.profile.email){
            option.selected = true;
        }
        select.appendChild(option);
    });

    if(recommendation){
        suggestedDoctorName.innerText = recommendation.profile.name + " (" + (recommendation.profile.specialty || "General Panchakarma") + ")";
        suggestedDoctorReason.innerText = recommendation.reason;
        if(manualDoctorHint){
            manualDoctorHint.innerText = "System preselected the best doctor. You can still choose another doctor.";
        }
    }else{
        suggestedDoctorName.innerText = "No doctor suggested yet";
        suggestedDoctorReason.innerText = "Choose your health issue or complete analysis to get a recommendation.";
        if(manualDoctorHint){
            manualDoctorHint.innerText = "Choose doctor manually.";
        }
    }

    if(doctorMatchList){
        rankedDoctors.slice(0, 3).forEach((rankedItem, index)=>{
            const li = document.createElement("li");
            li.innerText =
            (index + 1) + ". Dr. " + rankedItem.profile.name +
            " (" + (rankedItem.profile.specialty || "General Panchakarma") + ") - " +
            rankedItem.reason;
            doctorMatchList.appendChild(li);
        });
    }
}

function showDoctorLoginForm(){
    document.getElementById("doctorLoginForm").style.display = "block";
    document.getElementById("doctorRegisterForm").style.display = "none";
}

function showDoctorRegisterForm(){
    document.getElementById("doctorLoginForm").style.display = "none";
    document.getElementById("doctorRegisterForm").style.display = "block";
}

function registerDoctor(){
    const name = document.getElementById("doctorNameInput").value.trim();
    const email = normalizeEmail(document.getElementById("doctorEmailInput").value);
    const hospital = document.getElementById("doctorHospitalInput").value.trim();
    const specialty = document.getElementById("doctorSpecialtyInput").value;
    const password = document.getElementById("doctorPasswordInput").value;
    const profiles = getDoctorProfiles();

    if(name === "" || email === "" || hospital === "" || specialty === "" || password === ""){
        showAIPopup("Enter doctor name, email, hospital, specialty, and password","error");
        return;
    }

    if(!isValidEmail(email)){
        showAIPopup("Enter a valid doctor email address","error");
        return;
    }

    if(password.length < 6){
        showAIPopup("Doctor password must be at least 6 characters","error");
        return;
    }

    const alreadyExists = profiles.some((profile)=>normalizeEmail(profile.email || "") === email);
    if(alreadyExists){
        showAIPopup("Doctor email already registered","warning");
        return;
    }

    profiles.push({
        name:name,
        email:email,
        password:password,
        hospital:hospital,
        specialty:specialty,
        createdAt:new Date().toISOString()
    });
    saveDoctorProfiles(profiles);
    document.getElementById("doctorNameInput").value = "";
    document.getElementById("doctorEmailInput").value = "";
    document.getElementById("doctorHospitalInput").value = "";
    document.getElementById("doctorSpecialtyInput").value = "";
    document.getElementById("doctorPasswordInput").value = "";
    document.getElementById("doctorEmail").value = email;
    showAIPopup("Doctor registered successfully. You can login now.","success");
    showDoctorLoginForm();
    resetDoctorLoginForm();
}

function setButtonState(id, disabled, label){
    const button = document.getElementById(id);
    if(!button){
        return;
    }

    button.disabled = disabled;
    if(label){
        button.innerText = label;
    }
}

const patientPages = ["dashboardPage", "symptomPage", "resultPage", "appointmentPage", "panchakarmaPage"];
const pagesWithSidebar = [...patientPages, "doctorPage"];

function updateGoogleStatus(message){
    const status = document.getElementById("googleLoginStatus");
    if(status){
        status.innerText = message;
    }
}

function isFirebaseConfigured(){
    return !!(
        window.firebase &&
        firebase.apps &&
        firebase.apps.length &&
        firebaseConfig.apiKey !== "YOUR_API_KEY" &&
        firebaseConfig.authDomain !== "YOUR_PROJECT.firebaseapp.com"
    );
}

async function signInWithGoogle(){
    if(!isFirebaseConfigured()){
        updateGoogleStatus("Fill your real Firebase config first, then try Google login again.");
        showAIPopup("Firebase config is still using placeholder values","warning");
        return;
    }

    try{
        const provider = new firebase.auth.GoogleAuthProvider();
        provider.setCustomParameters({
            prompt:"select_account"
        });

        const result = await firebase.auth().signInWithPopup(provider);
        const user = result.user;

        localStorage.setItem("patientName", user.displayName || user.email || "Google User");
        localStorage.setItem("email", user.email || "");
        localStorage.setItem("age", "");
        localStorage.setItem("progress", localStorage.getItem("progress") || "Not Started");
        localStorage.setItem("googleProfile", JSON.stringify({
            name:user.displayName || "",
            email:user.email || "",
            picture:user.photoURL || "",
            uid:user.uid || ""
        }));

        updateGoogleStatus("Signed in with Firebase Google authentication.");
        showAIPopup("Google login successful","success");
        setTimeout(()=>{
            showPage("dashboardPage");
        },500);
    }catch(error){
        console.error(error);
        updateGoogleStatus(error.message || "Google login failed.");
        showAIPopup("Google login failed","error");
    }
}

function showLogin(){
    document.getElementById("loginForm").style.display="block";
    document.getElementById("registerForm").style.display="none";
    updateGoogleStatus("Continue with Google is ready after your Firebase config is filled and Google sign-in is enabled.");
}

function showRegister(){
    document.getElementById("loginForm").style.display="none";
    document.getElementById("registerForm").style.display="block";
}

function resetDoctorLoginForm(){
    const doctorEmails = getDoctorProfiles().map((profile)=>profile.email).filter(Boolean);
    document.getElementById("doctorEmailHint").innerText = doctorEmails.length ? doctorEmails.join(", ") : "No doctor registered yet";
    document.getElementById("doctorLoginForm").style.display = "block";
    document.getElementById("doctorRegisterForm").style.display = "none";
}

function showPage(page, addToHistory=true){
    const pageElement = document.getElementById(page);
    if(!pageElement){
        showAIPopup("Page not found","error");
        return;
    }

    if(addToHistory){
        try{
            window.history.pushState({page:page}, "", "#" + page);
        }catch(error){
        }
    }

    document.querySelectorAll(".page").forEach((section)=>{
        section.style.display="none";
    });
    pageElement.style.display="block";

    const patientLayout = document.getElementById("patientLayout");
    const isPatientPage = patientPages.includes(page);
    if(patientLayout){
        patientLayout.style.display = pagesWithSidebar.includes(page) ? "block" : "none";
    }

    document.querySelectorAll(".sidebar-link[data-page]").forEach((link)=>{
        link.classList.toggle("is-active", link.getAttribute("data-page") === page);
    });

    if(page==="dashboardPage"){
        document.getElementById("patientName").innerText = localStorage.getItem("patientName") || "Patient";
    }

    if(page==="resultPage"){
        loadResult();
    }

    if(page==="appointmentPage"){
        updatePatientStatus();
        updateDoctorRecommendation();
    }

    if(page==="doctorLoginPage"){
        resetDoctorLoginForm();
    }

    if(page==="doctorPage"){
        if(localStorage.getItem("doctorLoggedIn")!=="true"){
            showAIPopup("Access denied. Doctor login required.","error");
            showPage("doctorLoginPage");
            return;
        }
        loadAppointments();
        document.getElementById("doctorDisplayName").innerText = localStorage.getItem("doctorName") || "Doctor";
        document.getElementById("doctorDisplaySpecialty").innerText = localStorage.getItem("doctorSpecialty") || "Not assigned";
    }
}

window.onpopstate = function(event){
    if(event.state && event.state.page){
        showPage(event.state.page,false);
    }
};

function register(){
    const terms=document.getElementById("termsCheck").checked;
    const name=document.getElementById("nameInput").value.trim();
    const email=normalizeEmail(document.getElementById("emailInput").value);
    const age=document.getElementById("ageInput").value.trim();
    const password=document.getElementById("passwordInput").value;

    if(!terms){
        showAIPopup("Please accept Terms & Conditions","error");
        return;
    }

    if(name==="" || email==="" || age==="" || password===""){
        showAIPopup("Please fill all fields","error");
        return;
    }

    if(!isValidEmail(email)){
        showAIPopup("Enter a valid email address","error");
        return;
    }

    if(isNaN(age) || Number(age) <= 0){
        showAIPopup("Enter a valid age","error");
        return;
    }

    if(password.length < 6){
        showAIPopup("Password must be at least 6 characters","error");
        return;
    }

    if(localStorage.getItem("user_" + email)){
        showAIPopup("Account already exists. Please login.","warning");
        return;
    }

    localStorage.setItem("user_" + email, JSON.stringify({
        name:name,
        email:email,
        age:age,
        password:password
    }));

    document.getElementById("loginName").value = name;
    document.getElementById("loginEmail").value = email;
    document.getElementById("loginPassword").value = password;
    showAIPopup("Registration successful","success");

    setTimeout(()=>{
        showLogin();
    },500);
}

function verifyAndStoreUser(email){
    const user = JSON.parse(localStorage.getItem("user_" + email));
    if(!user){
        showAIPopup("User not found. Please register again.","error");
        return null;
    }

    localStorage.setItem("patientName",user.name);
    localStorage.setItem("email",user.email || "");
    localStorage.setItem("age",user.age);
    localStorage.setItem("progress", localStorage.getItem("progress") || "Not Started");
    return user;
}

function login(){
    const name = document.getElementById("loginName").value.trim();
    const email = normalizeEmail(document.getElementById("loginEmail").value);
    const password = document.getElementById("loginPassword").value;

    if(name === "" || email === "" || password === ""){
        showAIPopup("Enter name, email, and password","error");
        return;
    }

    if(!isValidEmail(email)){
        showAIPopup("Enter a valid email address","error");
        return;
    }

    const storedUser = localStorage.getItem("user_" + email);
    if(!storedUser){
        showAIPopup("Account not found. Please register first.","error");
        return;
    }

    const user = JSON.parse(storedUser);
    if(user.name.trim().toLowerCase() !== name.toLowerCase()){
        showAIPopup("Name does not match this email","error");
        return;
    }
    if((user.password || "") !== password){
        showAIPopup("Password is incorrect","error");
        return;
    }

    const loggedInUser = verifyAndStoreUser(email);
    if(!loggedInUser){
        return;
    }

    showAIPopup("Login successful","success");
    setTimeout(()=>{
        showPage("dashboardPage");
    },500);
}

function doctorLogin(){
    const email = normalizeEmail(document.getElementById("doctorEmail").value);
    const password = document.getElementById("doctorPassword").value;
    const doctorProfiles = getDoctorProfiles();

    if(doctorProfiles.length === 0){
        showAIPopup("No doctor is registered yet. Use Doctor Register first.","warning");
        showDoctorRegisterForm();
        return;
    }

    if(email === "" || password === ""){
        showAIPopup("Enter doctor email and password","error");
        return;
    }

    if(!isValidEmail(email)){
        showAIPopup("Enter a valid doctor email address","error");
        return;
    }

    const doctorProfile = doctorProfiles.find((profile)=>normalizeEmail(profile.email || "") === email);
    if(!doctorProfile){
        showAIPopup("This doctor email is not authorized for login","error");
        return;
    }

    if((doctorProfile.password || "") !== password){
        showAIPopup("Doctor password is incorrect","error");
        return;
    }

    localStorage.setItem("doctorLoggedIn","true");
    localStorage.setItem("doctorName", doctorProfile.name || "");
    localStorage.setItem("doctorEmail", doctorProfile.email || "");
    localStorage.setItem("doctorSpecialty", doctorProfile.specialty || "General Panchakarma");
    showAIPopup("Doctor login successful","success");
    setTimeout(()=>{
        showPage("doctorPage");
    },500);
}

function doctorLogout(){
    localStorage.removeItem("doctorLoggedIn");
    localStorage.removeItem("doctorName");
    localStorage.removeItem("doctorEmail");
    localStorage.removeItem("doctorSpecialty");
    showAIPopup("Doctor logged out","warning");
    setTimeout(()=>{
        showPage("loginPage");
    },500);
}

function bookAppointment(){
    const date=document.getElementById("appointDate").value;
    const time=document.getElementById("appointTime").value;
    const issue=document.getElementById("patientIssue").value;
    let doctorEmail=document.getElementById("doctorSelect").value;
    const patient=localStorage.getItem("patientName");
    const profiles=getDoctorProfiles();

    if(doctorEmail === ""){
        const recommendation = getRecommendedDoctor(issue);
        if(recommendation){
            doctorEmail = recommendation.profile.email;
        }
    }

    const selectedDoctor=profiles.find((profile)=>profile.email===doctorEmail);

    if(!patient){
        showAIPopup("Please login first","error");
        return;
    }

    if(issue==="" || doctorEmail==="" || !selectedDoctor){
        showAIPopup("Please choose health issue and doctor","error");
        return;
    }

    if(date==="" || time===""){
        showAIPopup("Please select date and time","error");
        return;
    }

    const appointments=JSON.parse(localStorage.getItem("appointments")) || [];
    appointments.push({
        id:Date.now(),
        patient:patient,
        issue:issue,
        doctorName:selectedDoctor.name,
        doctorEmail:selectedDoctor.email,
        doctorSpecialty:selectedDoctor.specialty || "General Panchakarma",
        dosha:localStorage.getItem("finalDosha") || "Not analyzed",
        therapy:localStorage.getItem("therapy") || "Not assigned",
        progress:localStorage.getItem("progress") || "Not Started",
        date:date,
        time:time,
        status:"Pending",
        suggestedBySystem:document.getElementById("suggestedDoctorName").innerText.includes(selectedDoctor.name)
    });
    localStorage.setItem("appointments",JSON.stringify(appointments));

    document.getElementById("appointStatus").innerText = "Appointment booked with Dr. " + selectedDoctor.name + " (" + (selectedDoctor.specialty || "General Panchakarma") + ")";
    showAIPopup("Appointment booked","success");
}

function updatePatientStatus(){
    const appointments=JSON.parse(localStorage.getItem("appointments")) || [];
    const patient=localStorage.getItem("patientName");
    const latest=[...appointments].reverse().find((appointment)=>appointment.patient===patient);
    document.getElementById("appointStatus").innerText = latest ? (latest.status + " with Dr. " + (latest.doctorName || "Assigned Doctor")) : "No appointment booked";
}

function loadAppointments(){
    const list=document.getElementById("appointmentList");
    const appointments=JSON.parse(localStorage.getItem("appointments")) || [];
    const doctorEmail=localStorage.getItem("doctorEmail");
    list.innerHTML="";

    const doctorAppointments = appointments.filter((appointment)=>appointment.doctorEmail===doctorEmail);

    const latestAppointment = doctorAppointments.length ? doctorAppointments[doctorAppointments.length - 1] : null;
    document.getElementById("docPatient").innerText = latestAppointment ? latestAppointment.patient : "Not available";
    document.getElementById("docDosha").innerText = latestAppointment ? (latestAppointment.dosha || "Not analyzed") : "Not analyzed";
    document.getElementById("docTherapy").innerText = latestAppointment ? (latestAppointment.therapy || "Not assigned") : "Not assigned";
    document.getElementById("docProgress").innerText = latestAppointment ? (latestAppointment.progress || "Not Started") : "Not Started";

    if(doctorAppointments.length===0){
        const empty=document.createElement("li");
        empty.className="list-group-item";
        empty.innerText="No appointments for this doctor yet.";
        list.appendChild(empty);
        return;
    }

    doctorAppointments.forEach((appointment)=>{
        const item=document.createElement("li");
        item.className="list-group-item";
        item.innerHTML =
        "<b>" + appointment.patient + "</b><br>" +
        "Issue: " + (appointment.issue || "General consultation") + "<br>" +
        "Booked via: " + (appointment.suggestedBySystem ? "System suggestion" : "Manual doctor choice") + "<br>" +
        "Date: " + appointment.date + " | Time: " + appointment.time + "<br>" +
        "Status: <b>" + (appointment.status || "Pending") + "</b>";
        list.appendChild(item);
    });
}

function toggleDarkMode(){
    document.body.classList.toggle("dark-mode");
    localStorage.setItem("darkMode", document.body.classList.contains("dark-mode"));
}

function logout(){
    localStorage.removeItem("patientName");
    localStorage.removeItem("email");
    localStorage.removeItem("age");
    localStorage.removeItem("googleProfile");
    showLogin();
    showPage("loginPage");
}

function toggleBox(id){
    document.getElementById(id).classList.toggle("active");
}

function analyze(){
    document.getElementById("loader").style.display="block";

    setTimeout(()=>{
        const v=document.querySelectorAll('input[name="vata"]:checked').length;
        const p=document.querySelectorAll('input[name="pitta"]:checked').length;
        const k=document.querySelectorAll('input[name="kapha"]:checked').length;

        localStorage.setItem("vata",v);
        localStorage.setItem("pitta",p);
        localStorage.setItem("kapha",k);

        let dosha="Kapha";
        if(v>p && v>k) dosha="Vata";
        else if(p>v && p>k) dosha="Pitta";

        localStorage.setItem("finalDosha",dosha);
        document.getElementById("loader").style.display="none";
        showPage("resultPage");
    },900);
}

function loadResult(){
    const dosha=localStorage.getItem("finalDosha") || "Not analyzed";
    let therapy="";
    let diet="";
    let description="";
    let image="";

    if(dosha==="Vata"){
        therapy="Basti Therapy (Medicated Enema)";
        diet="Warm foods, oil massage, proper sleep";
        description="Basti supports Vata balance, nourishes tissues, and helps improve digestion and nervous system stability.";
        image="images/Basti_Therapy.jpg";
    }else if(dosha==="Pitta"){
        therapy="Virechana Therapy (Purgation)";
        diet="Cooling foods, avoid spicy and oily meals";
        description="Virechana helps reduce excess Pitta, especially in acidity, skin irritation, and heat-related imbalance.";
        image="images/Virechana_therapy.jpg";
    }else if(dosha==="Kapha"){
        therapy="Vamana Therapy (Therapeutic Emesis)";
        diet="Light meals, regular exercise, and less heavy food";
        description="Vamana is traditionally used for Kapha imbalance and is often associated with respiratory and sluggishness concerns.";
        image="images/Vamana_therapy.jpg";
    }else{
        therapy="Complete the symptom analysis to see recommendations";
        diet="Balanced routine and light meals";
        description="Your therapy recommendation will appear after the analysis step.";
        image="images/logo.png";
    }

    localStorage.setItem("therapy",therapy);
    document.getElementById("doshaText").innerText=dosha;
    document.getElementById("therapyText").innerText=therapy;
    document.getElementById("dietText").innerText=diet;
    document.getElementById("therapyDescription").innerText=description;
    document.getElementById("therapyImage").src=image;
    document.getElementById("progressText").innerText = localStorage.getItem("progress") || "Not Started";

    createChart();
}

function createChart(){
    const v=+localStorage.getItem("vata") || 0;
    const p=+localStorage.getItem("pitta") || 0;
    const k=+localStorage.getItem("kapha") || 0;

    if(doshaChart){
        doshaChart.destroy();
    }

    doshaChart = new Chart(document.getElementById("chartCanvas"),{
        type:"pie",
        data:{
            labels:["Vata","Pitta","Kapha"],
            datasets:[{
                data:[v,p,k],
                backgroundColor:["#43a047","#ef5350","#42a5f5"]
            }]
        }
    });
}

function completeTreatment(){
    localStorage.setItem("progress","Completed");
    loadResult();
}

function downloadPDF(){
    const { jsPDF } = window.jspdf;
    const doc=new jsPDF();
    doc.text("E-Panchakarma Report",20,20);
    doc.text("Patient: " + (localStorage.getItem("patientName") || "N/A"),20,40);
    doc.text("Dosha: " + (localStorage.getItem("finalDosha") || "N/A"),20,50);
    doc.text("Therapy: " + (localStorage.getItem("therapy") || "N/A"),20,60);
    doc.save("E-Panchakarma-Report.pdf");
}

if(localStorage.getItem("darkMode")==="true"){
    document.body.classList.add("dark-mode");
}

showLogin();
showPage("loginPage", false);
