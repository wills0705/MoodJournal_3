import api from './request';



const url = {
  generateTopic: '/associate_moods_with_topics',
    chatUrl: '/chat'
}

const generateTopic = (text) => {
  return api.post(url.generateTopic, { text })
}

const getLog = (text) => {
  return api.post(url.chatUrl, text)
}

export {
  getLog,
  generateTopic,
}