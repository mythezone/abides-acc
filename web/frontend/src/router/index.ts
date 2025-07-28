import { createRouter, createWebHistory } from "vue-router"
import MarketView from "../views/MarketView.vue"
import AgentView from "../views/AgentView.vue"


const routes = [
    { path: '/', redirect: '/market' },
  { path: '/market', name: 'MarketView', component: MarketView },
  { path: '/agent', name: 'AgentView', component: AgentView }
];

export default createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});
