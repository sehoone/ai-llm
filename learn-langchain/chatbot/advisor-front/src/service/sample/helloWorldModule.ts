import { defineStore } from 'pinia';
import type { HellowModel } from '@/service/sample/model/helloWorldModel';
import { getHellowText } from '@/service/sample/helloWorldApi';

interface HelloWorldState {
  helloText: string;
}

export const useHelloWorldStore = defineStore({
  id: 'app-hello-world',
  state: (): HelloWorldState => ({
    helloText: ''
  }),
  getters: {
    getHelloText(): string {
      return this.helloText || '';
    }
  },
  actions: {
    setHelloText(helloText: string) {
      this.helloText = helloText ? helloText : '';
    },
    /**
     * @description: reqHelloText
     */
    async reqHelloText(): Promise<HellowModel> {
      try {
        const data = await getHellowText();
        const { helloText } = data;

        // save helloText
        this.setHelloText(helloText);
        return data;
      } catch (error) {
        return Promise.reject(error);
      }
    }
  }
});

// Need to be used outside the setup
// const helloWorldStoreWithOut = helloWorldStore(pinia);

// export function useHelloWorldStore(): typeof helloWorldStoreWithOut {
//   return helloWorldStoreWithOut;
// }

/*
const state: State = {
  helloText: '',
};

const getters: GetterTree<State, undefined> = {
  getHelloText: (state) => state.helloText || '',
};

const mutations: MutationTree<State> = {
  setHelloText: (state: State, helloText: string) => {
    state.helloText = helloText ? helloText : '';
  },
};

const actions: ActionTree<State, undefined> = {
  async reqHelloText(
    store: ActionContext<State, undefined>
  ): Promise<HellowModel> {
    try {
      const data = await getHellowText();
      const { helloText } = data;

      // save helloText
      store.commit('setHelloText', helloText);
      return data;
    } catch (error) {
      return Promise.reject(error);
    }
  },
};

export default {
  namespaced: true,
  state,
  getters,
  actions,
  mutations,
};
*/
