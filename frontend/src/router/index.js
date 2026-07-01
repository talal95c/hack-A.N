import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Process from '../views/MainView.vue'
import SimulationView from '../views/SimulationView.vue'
import SimulationRunView from '../views/SimulationRunView.vue'
import ReportView from '../views/ReportView.vue'
import InteractionView from '../views/InteractionView.vue'
import ScenariosView from '../views/ScenariosView.vue'
import ScenarioDetailView from '../views/ScenarioDetailView.vue'
import ComparisonView from '../views/ComparisonView.vue'
import BacktestingView from '../views/BacktestingView.vue'
import AdminView from '../views/AdminView.vue'
import LoginView from '../views/LoginView.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/scenarios',
    name: 'Scenarios',
    component: ScenariosView
  },
  {
    path: '/scenario-detail/:scenarioId',
    name: 'ScenarioDetail',
    component: ScenarioDetailView,
    props: true
  },
  {
    path: '/comparison',
    name: 'Comparison',
    component: ComparisonView
  },
  {
    path: '/backtesting',
    name: 'Backtesting',
    component: BacktestingView
  },
  {
    path: '/admin',
    name: 'Admin',
    component: AdminView
  },
  {
    path: '/login',
    name: 'Login',
    component: LoginView
  },
  {
    path: '/process/:projectId',
    name: 'Process',
    component: Process,
    props: true
  },
  {
    path: '/simulation/:simulationId',
    name: 'Simulation',
    component: SimulationView,
    props: true
  },
  {
    path: '/simulation/:simulationId/start',
    name: 'SimulationRun',
    component: SimulationRunView,
    props: true
  },
  {
    path: '/report/:reportId',
    name: 'Report',
    component: ReportView,
    props: true
  },
  {
    path: '/interaction/:reportId',
    name: 'Interaction',
    component: InteractionView,
    props: true
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
