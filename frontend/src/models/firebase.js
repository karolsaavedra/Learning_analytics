// Firebase Configuration — Model Layer
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js";
import { getFirestore, collection, addDoc, onSnapshot, query, orderBy, limit } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore.js";
import { getAuth, signInWithEmailAndPassword, signOut, onAuthStateChanged } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js";

const firebaseConfig = {
  apiKey: "AIzaSyDhug3B-1Kq6YseNYVmLRO8Qvk7P4tCkbU",
  authDomain: "prediccionriesgoacademico.firebaseapp.com",
  projectId: "prediccionriesgoacademico",
  storageBucket: "prediccionriesgoacademico.firebasestorage.app",
  messagingSenderId: "237142462692",
  appId: "1:237142462692:web:36b7708f8a9ded59bc1cf1"
};

const app = initializeApp(firebaseConfig);
export const db = getFirestore(app);
export const auth = getAuth(app);

export { collection, addDoc, onSnapshot, query, orderBy, limit, signInWithEmailAndPassword, signOut, onAuthStateChanged };
