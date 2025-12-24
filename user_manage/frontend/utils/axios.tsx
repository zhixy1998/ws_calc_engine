import axios from "axios";

// 创建一个axios实例
const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  timeout: 5000,
});

//请求拦截器
api.interceptors.request.use(
  (config) => {
    const token =
      typeof window !== "undefined"
        ? window.localStorage.getItem("user_manage_token")
        : null;
    if (token) {
      config.headers["Authorization"] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    if (response.data && response.data.code === 401) {
      if (typeof window !== "undefined") {
        window.location.href = "/user_manage_verify";
      }
    }
    return response;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export default api;
