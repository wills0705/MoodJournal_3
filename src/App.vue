<template>
  <div class="mood-journal-app">
    <div class="mood-journal-app-content">
      <!-- Authentication Components -->
      <div v-if="!isAuthenticated">
        <Signup v-if="showSignup" @switch-auth="toggleAuthForm" />
        <Login v-else @switch-auth="toggleAuthForm" />
      </div>

      <!-- Main App Components -->
      <div class="app-container" v-else>
        <div class="mood-journal-app-content-header">
          <div
            :class="['tab-item', activeIndex === index ? 'active-item' : '']"
            v-for="(item, index) in tabList"
            :key="index"
            @click="handleClick(index)"
          >
            {{ item.name }}
          </div>
          <button @click="logout" class="logout-button">Log Out</button>
        </div>
        <div class="mood-journal-app-content-content">
          <keep-alive exclude="analysis">
            <component
              :is="currentComponent"
              :journalList="journalList"
              :saveStatus="saveStatus"
              @updateJournal="handleUpdate"
            />
          </keep-alive>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import Write from './views/Write';
import Journal from './views/Journal';
import Analysis from './views/Analysis';

import Signup from './components/Signup.vue';
import Login from './components/Login.vue';

import { auth, db } from './firebase';
import {
  collection,
  addDoc,
  query,
  orderBy,
  onSnapshot,
  where,
  getDocs
} from 'firebase/firestore';
import {
  getStorage,
  ref,
  uploadBytes,
  getDownloadURL
} from "firebase/storage";
import { onAuthStateChanged, signOut } from 'firebase/auth';

export default {
  components: { Write, Journal, Analysis, Signup, Login },
  data() {
    return {
      journalList: [],
      tabList: [
        { name: 'Write new',    componentName: 'write' },
        { name: 'Prev Journal', componentName: 'journal' },
        { name: 'Analytics',    componentName: 'analysis' },
      ],
      activeIndex: 0,
      currentComponent: 'write',
      isAuthenticated: false,
      showSignup: false,
      saveStatus: 'idle',

      _unsub: null,
      _prevFlags: new Map(),
      _ding: null
    };
  },
  created() {
    // prepare audio
    this._ding = new Audio('/sounds/notify.wav');
    this._ding.preload = 'auto';
    this._ding.volume = 1.0;

    onAuthStateChanged(auth, (user) => {
      if (this._unsub) { this._unsub(); this._unsub = null; }
      // reset transition memory on user switch/sign-out
      this._prevFlags.clear();

      if (user) {
        this.isAuthenticated = true;
        this.startRealtime(user.uid); // live updates with fallback
      } else {
        this.isAuthenticated = false;
        this.journalList = [];
      }
    });
  },
  beforeUnmount() {
    if (this._unsub) { this._unsub(); this._unsub = null; }
  },
  methods: {
    toggleAuthForm() { this.showSignup = !this.showSignup; },
    async logout() {
      try {
        await signOut(auth);
        this.$message?.success('Logged out successfully');
      } catch (error) {
        console.error('Error logging out:', error);
        this.$message?.error('Failed to log out');
      }
    },
    handleClick(index) {
      this.activeIndex = index;
      this.currentComponent = this.tabList[index].componentName;
    },

    playDing() {
      this._ding?.play().catch(() => {});
    },

    _checkTransitions(rows) {
      for (const r of rows) {
        const key = r.id;
        const prev = this._prevFlags.get(key) || { img: false, ther: false };

        const imgNow  = r.isApproved === true;
        const therNow = r.therapyApproved === true;

        // fire on rising edges only
        if (imgNow && !prev.img)  this.playDing();
        if (therNow && !prev.ther) this.playDing();

        // store current state
        this._prevFlags.set(key, { img: imgNow, ther: therNow });
      }
    },

    // ===== Realtime with graceful fallback =====
    startRealtime(userId) {
      const qRef = query(
        collection(db, 'journalList'),
        where('userId', '==', userId),
        orderBy('timestamp', 'desc')
      );
      this._unsub = onSnapshot(
        qRef,
        (snap) => {
          const rows = [];
          snap.forEach((d) => rows.push({ id: d.id, ...d.data() }));
          this._checkTransitions(rows);
          this.journalList = rows; // server-sorted
        },
        (err) => {
          console.warn('onSnapshot error:', err);
          if (String(err.code).toLowerCase().includes('failed-precondition')) {
            this.startRealtimeNoIndex(userId);
          } else {
            this.journalList = [];
          }
        }
      );
    },

    // Fallback: where only, sort on client (no composite index required)
    startRealtimeNoIndex(userId) {
      if (this._unsub) { this._unsub(); this._unsub = null; }
      const qRef = query(
        collection(db, 'journalList'),
        where('userId', '==', userId)
      );
      this._unsub = onSnapshot(
        qRef,
        (snap) => {
          const rows = [];
          snap.forEach((d) => rows.push({ id: d.id, ...d.data() }));
          rows.sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0));
          this._checkTransitions(rows);
          this.journalList = rows;
        },
        (err) => {
          console.error('onSnapshot fallback error:', err);
          this.journalList = [];
        }
      );
    },

    async handleUpdate(obj) {
      this.saveStatus = 'saving';
      try {
        const user = auth.currentUser;
        if (!user) {
          this.$message?.error('You must be logged in.');
          this.saveStatus = 'idle';
          return;
        }
        obj.userId = user.uid;
        obj.userEmail = user.email;
        obj.timestamp = Date.now();
        obj.mood = 2;
        obj.mood2 = 2;
        obj.sdImage = "";

        const presetMap = {
          1: "line-art",
          2: "comic-book",
          3: "pixel-art",
          4: "analog-film",
          5: "neon-punk"
        };
        const style_preset = presetMap[obj.buttonNumber] || "digital-art";
        const prompt = `${obj.content}`;

        // Condition-3 backend
        const response = await fetch('https://moodjournal-3-api-isp9.onrender.com/api/generate-image', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt, style_preset }),
        });
        if (!response.ok) throw new Error('Failed to generate image');

        const data = await response.json();
        const imageUrlOnBackend = `https://moodjournal-3-api-isp9.onrender.com${data.image_url}`;

        // Upload to Firebase Storage
        const storage = getStorage();
        const storageRef = ref(storage, `generated_images/${Date.now()}.jpg`);
        const fetched = await fetch(imageUrlOnBackend);
        const blob = await fetched.blob();
        const snapshot = await uploadBytes(storageRef, blob);
        const downloadURL = await getDownloadURL(snapshot.ref);
        obj.sdImage = downloadURL;

        await addDoc(collection(db, 'journalList'), obj);
        this.$message?.success('Journal entry saved successfully');
        this.saveStatus = 'success';
        setTimeout(() => (this.saveStatus = 'idle'), 800);
      } catch (error) {
        console.error('Error adding document:', error);
        this.$message?.error('Failed to save journal entry');
        this.saveStatus = 'error';
        setTimeout(() => (this.saveStatus = 'idle'), 1200);
      }
    },

    // (Optional) one-off fetch kept for reference
    async fetchJournalList() {
      try {
        const userId = auth.currentUser.uid;
        const q = query(collection(db, 'journalList'), orderBy('timestamp', 'desc'));
        const querySnapshot = await getDocs(q);
        this.journalList = querySnapshot.docs
          .map((doc) => ({ id: doc.id, ...doc.data() }))
          .filter((entry) => entry.userId === userId);
      } catch (error) {
        console.error('Error fetching journalList:', error);
        this.journalList = [];
      }
    },
  },
};
</script>

<style lang="less" scoped>
.mood-journal-app {
  height: 100%;
  background: #fff;
  display: flex;
  justify-content: center;

  &-content {
    width: 80%;
    background: #f3f4f6;
    height: 100%;
    padding: 20px;
    display: flex;
    flex-direction: column;

    .app-container { height: 100%; display: flex; flex-direction: column; }

    &-header {
      flex: none;
      display: flex;
      align-items: center;
      justify-content: space-around;

      .tab-item {
        padding: 4px 20px;
        border-radius: 12px;
        transition: font-size 0.1s ease;
        cursor: pointer;
      }

      .active-item {
        font-size: 18px;
        font-weight: bold;
        color: green;
        background-color: #99CC99;
      }
    }

    &-content { flex: auto; overflow: hidden; margin-top: 20px; }
  }
}

.logout-button {
  margin-left: auto;
  padding: 4px 12px;
  background-color: #f44336;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}
</style>
