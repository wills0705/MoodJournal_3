<template>
  <div class="journal-list">
    <div class="journal-list-list">
      <div
        :class="[
          'list-item',
          currentJournal.timestamp === item.timestamp ? 'active-item' : '',
        ]"
        v-for="(item, index) in list"
        :key="index"
        @click="showJournalDetail(item)"
      >
        <div class="list-item-title">
          {{ item.title }}
        </div>
        <div class="list-item-date">
          {{ item.enDate }}
        </div>
      </div>
    </div>

    <div class="journal-list-content" v-if="currentJournal.content">
      <!-- Left Panel: Journal Info -->
      <div class="journal-list-content-left">
        <div class="content-title">
          <div class="content-title-text">
            <div class="month">{{ currentJournal.enDate.slice(0, -5) }}</div>
            <div class="week">
              {{ currentJournal.enDate.slice(-4) }},
              {{ currentJournal.weekDay }}
            </div>
          </div>
          <div class="content-title-icon">
            <img :src="currentFace" alt="" class="mood-icon" />
          </div>
        </div>

        <div class="content-container">
          <div class="content-container-title">
            {{ currentJournal.title }}
          </div>
          <div class="content-container-content">
            {{ currentJournal.content }}
          </div>
        </div>

        <div class="content-rate">
          <div class="content-rate-tip">Rate your mood today</div>
          <div class="content-rate-icon">
            <img
              style="width: 50px; height: 50px"
              v-for="(item, index) in faceList"
              :key="index"
              :src="faceIconUrl(item)"
              class="mood-icon"
              @click="setFace(item, index)"
            />
          </div>
          <button
            style="
              padding: 10px 20px;
              background-color: #007bff;
              color: white;
              border: none;
              border-radius: 5px;
              cursor: pointer;
            "
            @click="openModal"
            id="openModalBtn"
          >
            create a therapy
          </button>
        </div>
      </div>
     <!-- 模态框结构 -->

      <!-- Right Panel: AI Image (base64) or fallback cat -->
      <div class="journal-list-content-right">
        <div class="content-img">
          <template v-if="currentJournal.isApproved">
            <img
              :src="currentJournal.sdImage"
              alt="Generated Image"
              class="ai-img"
              @error="handleImageError"
            />
          </template>
          <div v-else class="pending-message">
            The picture is successfully generated, please wait patiently for
            review.
          </div>
          <div class="img-text">AI-Generated Image</div>
        </div>
      </div>
    </div>
  </div>
<div 
  class="modal-overlay" 
  id="modalOverlay" 
  style="z-index:10000"
  :class="{ active: isModalActive }"
  @click.self="closeModal" 
>
  <div class="modal-card" @click.stop> <!-- 阻止点击卡片关闭 -->
    <span class="close-btn" @click="closeModal">&times;</span>
    
    <div class="modal-header">
      <div class="modal-title-container">
        <h2 class="modal-title">Therapy by AI</h2>
        <div class="therapy-rating-icon">
          <img :src="faceIconUrl(faceList[currentJournal.mood2])" alt="therapy mood" />
        </div>
      </div>
      <span class="close-btn" @click="closeModal">&times;</span>
    </div>

    <div class="modal-content">
      <div class="content-text">
        {{ modalContent || "Analyzing..." }}
      </div>
      <div class="content-rate">
        <div class="content-rate-tip">
          Rate this therapy
        </div>
        <div class="content-rate-icons">
          <img
            v-for="(item, index) in faceList"
            :key="index"
            :src="faceIconUrl(item)"
            class="mood-icon"
            @click="setFace1(item, index)"
          />
        </div>
      </div>
    </div>
</div>
</div>
</template>

<script>
import { doc, updateDoc } from "firebase/firestore";
import { db } from "../firebase";
import { dayMap, monthMap } from "../lib/util";
import { getLog } from "../api/api";
import moodSad from '../assets/image/mood-sad.png'
import moodFrown from '../assets/image/mood-frown.png'
import moodNormal from '../assets/image/mood-normal.png'
import moodSmile from '../assets/image/mood-smile.png'
import moodLaugh from '../assets/image/mood-laugh.png'

export default {
  name: "journal",
  props: {
    journalList: {
      type: Array,
      default: [],
    },
  },
  data() {
    return {
      list: [],
      isModal: false,
      currentJournal: {
        id: "",
        title: "",
        content: "",
        currentDate: "",
        timestamp: "",
        mood: 2,
        mood2: 2,
        sdImage: "",
        therapy: "",
      },
      faceList: [
        moodSad,
        moodFrown,
        moodNormal,
        moodSmile,
        moodLaugh
      ],
      currentFace: "",
      fallbackCat: "",
      modalContent: null,
      isModalActive: false,
    };
  },
  watch: {
    journalList() {
      this.filterJournal();
    },
  },
  methods: {
    setFace(item, index) {
      this.currentFace = this.faceIconUrl(item);
      if (this.currentJournal.mood !== index) {
        this.currentJournal.mood = index;
        this.updateJournalMood('mood', index);
      }
    },

    setFace1(item, index) {
      if (this.currentJournal.mood2 !== index) {
        this.currentJournal.mood2 = index;
        this.updateJournalMood('mood2', index);
      }
    },

    async updateJournalMood(field, value) {
      if (!this.currentJournal.id || !['mood', 'mood2'].includes(field)) return;
      try {
        const docRef = doc(db, "journalList", this.currentJournal.id);
        await updateDoc(docRef, { [field]: value });
        this.$message && this.$message.success("Mood updated successfully!");
      } catch (err) {
        console.error("Error updating mood in Firestore:", err);
      }
    },

    async openModal() {
      await this.$nextTick();
      this.isModalActive = true;
      if (this.currentJournal.therapy) {
        this.modalContent = this.currentJournal.therapy;
        return;
      }
      this.modalContent = "Generating...";
      try {
        const res = await getLog({ message: this.currentJournal.content });
        if (res.data.reply) {
          this.modalContent = res.data.reply;
          this.currentJournal.therapy = res.data.reply;
          await this.saveTherapyToFirestore(res.data.reply);
        }
      } catch (error) {
        console.error("获取解析失败:", error);
        this.modalContent = "Failed to fetch therapy.";
      }
    },
    async saveTherapyToFirestore(reply) {
      if (!this.currentJournal.id) return;
      try {
        const docRef = doc(db, "journalList", this.currentJournal.id);
        await updateDoc(docRef, { therapy: reply });
      } catch (err) {
        console.error("Error saving therapy to Firestore:", err);
      }
    },
    closeModal() {
      this.isModalActive = false;
      this.modalContent = "";
      document.removeEventListener('click', this.handleOutsideClick);
    },
    handleOutsideClick(event) {
      if (!this.$el.contains(event.target)) {
        this.closeModal();
      }
    },
    handleImageError(e) {
      e.target.src = this.fallbackCat;
    },
    faceIconUrl(path) {
      return new URL(path, import.meta.url).href;
    },
    showJournalDetail(journal) {
      this.currentJournal = { ...journal };
      if (journal.mood >= 0 && journal.mood < this.faceList.length) {
        this.currentFace = this.faceIconUrl(this.faceList[journal.mood]);
      } else {
        this.currentFace = this.faceIconUrl("../assets/image/mood-normal.png");
      }
    },
    filterJournal() {
      this.list = this.journalList.map((item) => {
        return {
          ...item,
          enDate: this.formatEnDate(item.currentDate),
          weekDay: this.getWeekDay(item.currentDate),
        };
      });
    },
    getWeekDay(date) {
      const d = new Date(date);
      return dayMap[d.getDay()];
    },
    formatEnDate(date) {
      const d = new Date(date);
      const m = monthMap[d.getMonth()].slice(0, 3);
      const dd = d.getDate();
      const y = d.getFullYear();
      return `${m}.${dd}.${y}`;
    },
  },
  mounted() {
    document.addEventListener('click', this.handleOutsideClick);
    this.filterJournal();
    this.fallbackCat = new URL("../assets/image/cat.jpeg", import.meta.url).href;
    this.currentFace = this.faceIconUrl("../assets/image/mood-normal.png");
  },
};
</script>

<style lang="less" scoped>
.pending-message {
  height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
  font-style: italic;
  padding: 20px;
  border: 2px dashed #eee;
  border-radius: 8px;
  margin: 20px 0;
}
.journal-list {
  height: 100%;
  overflow: hidden;
  display: flex;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  box-sizing: border-box;

  &-list {
    height: 100%;
    overflow: auto;
    width: 20%;
    background: rgb(244, 248, 255);

    .active-item {
      background: rgb(230, 235, 248);
    }

    .list-item {
      padding: 10px 16px;
      border-bottom: 1px solid rgba(0, 0, 0, 0.1);
      font-weight: bold;
      cursor: pointer;

      &-title {
        display: -webkit-box;
        -webkit-box-orient: vertical;
        -webkit-line-clamp: 2;
        overflow: hidden;
        text-overflow: ellipsis;
        word-break: break-all;
      }

      &-date {
        margin-top: 10px;
      }

      &:last-of-type {
        border-bottom: none;
      }

      &:hover {
        background: rgb(230, 235, 248);
      }
    }
  }

  &-content {
    height: 100%;
    width: 80%;
    flex: auto;
    display: flex;

    &-left {
      width: 50%;
      height: 100%;
      overflow: auto;
      padding: 20px;
      box-sizing: border-box;
      display: flex;
      flex-direction: column;

      .content-title {
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid rgba(0, 0, 0, 0.1);
        padding: 10px;

        &-text {
          .month {
            font-size: 24px;
            font-weight: bold;
          }

          .week {
            margin-top: 4px;
          }
        }

        &-icon {
          .mood-icon {
            width: 30px;
            height: 30px;
          }
        }
      }

      .content-container {
        padding: 20px;
        flex: auto;
        overflow: auto;

        &-title {
          font-size: 24px;
          font-weight: bold;
        }

        &-content {
          line-height: 20px;
          margin-top: 24px;
        }
      }

      .content-rate {
        padding: 20px 20px 0 20px;

        &-tip {
          font-size: 16px;
          font-weight: bold;
        }

        &-icon {
          display: flex;
          align-items: center;
          justify-content: center;

          .mood-icon {
            width: 100%;

            height: 40px;
            margin-left: 8px;
            margin-top: 10px;
            cursor: pointer;
          }
        }
      }

      .content-text {
        max-width: 100%;
        flex-wrap: wrap;
        padding: 20px;
        font-size: 16px;
        font-weight: bold;
      }
    }

    &-right {
      width: 50%;
      height: 100%;
      overflow: auto;
      padding: 20px;
      box-sizing: border-box;
      border-left: 1px solid rgba(0, 0, 0, 0.1);
      display: flex;
      flex-direction: column;

      .content-img {
        display: flex;
        align-items: center;
        justify-content: center;
        flex-direction: column;
        flex: auto;
        width: 100%;

        .ai-img {
          width: 100%;
          height: auto;
        }

        .img-text {
          margin-top: 20px;
        }
      }

      .content-tip {
        flex: none;
        color: rgba(198, 108, 116);
      }
    }
  }
}
/* 模态框背景 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: none;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

/* 模态框卡片 */
.modal-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
  max-width: 500px;
  width: 90%;
  text-align: center;
  padding: 24px;
  position: relative;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 5px;
}

.modal-title-container {
  display: flex;
  gap: 30px;
}

.therapy-rating-icon img {
  width: 30px;
  height: 30px;
  margin-bottom: 0px;
}


/* 关闭按钮 */
.close-btn {
  position: absolute;
  top: 16px;
  right: 20px;
  font-size: 28px;
  cursor: pointer;
  color: #666;
  transition: color 0.3s;
}

.close-btn:hover {
  color: #000;
}

/* 标题 */
.modal-title {
  text-align: center;
  font-size: 22px;
  font-weight: bold;
  margin-bottom: 24px;
  color: #333;
}

/* 内容区域 */
.modal-content {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

/* 内容文本 */
.content-text {
  width: 100%;
  max-width: 460px;
  height: 300px;               
  overflow-y: scroll;
  font-size: 16px;
  color: #333;
  margin: 20px 0;
  padding: 16px;
  box-sizing: border-box;
  word-wrap: break-word;
  word-break: break-word;
  line-height: 1.6;
  text-align: left;
  border: 1px solid #ddd;
  border-radius: 8px;
  background-color: #f9f9f9;
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.1);
}


/* 表情评分区域 */
.content-rate {
  margin-top: 24px;
  text-align: center;
  width: 100%;
}

.content-rate-tip {
  font-size: 16px;
  margin-bottom: 16px;
  color: #555;
}

.save-btn {
  padding: 8px 16px;
  font-size: 14px;
  color: #fff;
  background-color: #007bff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
  margin-left: 8px;
}

.save-btn:hover {
  background-color: #0056b3;
}

.content-rate-icons {
  display: flex;
  justify-content: center;
  gap: 20px;
}

.mood-icon {
  width: 40px;
  height: 40px;
  margin: 5px;
  cursor: pointer;
  transition: transform 0.3s;
  border-radius: 50%;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.mood-icon:hover {
  transform: scale(1.1);
}

.modal-overlay {
  display: none; /* 默认隐藏 */
  &.active {
    display: flex; /* 显示模态框 */
  }
}
</style>
