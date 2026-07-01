import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Process from '../views/MainView.vue'
import SimulationView from '../views/SimulationView.vue'
import SimulationRunView from '../views/SimulationRunView.vue'
import ReportView from '../views/ReportView.vue'
import InteractionView from '../views/InteractionView.vue'
import NewScenarioWizardView from '../views/NewScenarioWizardView.vue'

// Circuit unique (MiroFish v2, cf. GEMINI.md §3) :
// Home -> /process/new (upload) -> Process (ontologie+graphe+agents) -> Simulation (préparation)
// -> SimulationRun (débat OASIS) -> Report (recap + scénario tendanciel) -> Interaction (interview)
//
// Les routes de l'ancien "Circuit B" (bibliothèque de scénarios en DB, comparaison de lois,
// backtesting, admin, login) ont été retirées : leurs endpoints backend n'existent plus
// (voir CLAUDE.md/GEMINI.md pour l'historique du recadrage du backend).
const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/process/new',
    name: 'NewScenarioWizard',
    component: NewScenarioWizardView
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
