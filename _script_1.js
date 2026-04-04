
const firebaseConfig = {
    apiKey: "AIzaSyAZ3rkRDp7S8dxXT3vtB9raKtNqGThTf7k",
    authDomain: "e-panchkarma.firebaseapp.com",
    projectId: "e-panchkarma",
    storageBucket: "e-panchkarma.firebasestorage.app",
    messagingSenderId: "789217167561",
    appId: "1:789217167561:web:814b3bf1fc0346e7982518"
};

if(window.firebase && !firebase.apps.length){
    firebase.initializeApp(firebaseConfig);
}
