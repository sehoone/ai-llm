<template>
  <div>
    <v-navigation-drawer v-model="drawer" app>
      <v-list dense>
        <template v-for="item in items">
          <v-list-group
            v-if="item.children"
            :key="item.text"
            v-model="item.model"
            :prepend-icon="item.model ? item.icon : item['icon-alt']"
            append-icon=""
          >
            <template v-slot:activator>
              <v-list-item-content>
                <v-list-item-title>
                  {{ item.text }}
                </v-list-item-title>
              </v-list-item-content>
            </template>

            <v-list-item v-for="(child, i) in item.children" :key="i" link>
              <v-list-item-action v-if="child.icon">
                <v-icon>{{ child.icon }}</v-icon>
              </v-list-item-action>
              <v-list-item-content @click="clickGotoLink(child.link)">
                <v-list-item-title>
                  {{ child.text }}
                </v-list-item-title>
              </v-list-item-content>
            </v-list-item>
          </v-list-group>

          <v-list-item v-if="!item.children" :key="item.text" link>
            <v-list-item-action>
              <v-icon>{{ item.icon }}</v-icon>
            </v-list-item-action>
            <v-list-item-content @click="clickGotoLink(item.link)">
              <v-list-item-title>
                {{ item.text }}
              </v-list-item-title>
            </v-list-item-content>
          </v-list-item>
        </template>
      </v-list>
    </v-navigation-drawer>
    <v-app-bar app color="blue darken-3" dark>
      <v-app-bar-nav-icon @click.stop="drawer = !drawer"></v-app-bar-nav-icon>
      <v-toolbar-title style="width: 300px" class="ml-0 pl-4">
        <span class="hidden-sm-and-down">Sample Contacts</span>
      </v-toolbar-title>
      <v-text-field
        flat
        solo-inverted
        hide-details
        prepend-inner-icon="mdi-magnify"
        label="Search"
        class="hidden-sm-and-down"
      ></v-text-field>
      <v-spacer></v-spacer>
      <!--
      <v-btn icon>
        <v-icon>mdi-apps</v-icon>
      </v-btn>
      <v-btn icon>
        <v-icon>mdi-bell</v-icon>
      </v-btn>-->
      <v-btn icon large>
        <v-avatar size="32px" item>
          <v-img src="https://cdn.vuetifyjs.com/images/logos/logo.svg" alt="Vuetify"></v-img
        ></v-avatar>
      </v-btn>
    </v-app-bar>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();
// const route = useRoute();

// const dialog = ref(false);
const drawer = ref(false);
const items = ref([
  {
    icon: 'mdi-contacts',
    text: 'HelloWorld',
    link: '/sample/helloworld'
  },
  {
    icon: 'mdi-history',
    text: 'HelloWorld2',
    link: '/sample/helloworld2'
  },
  {
    icon: 'mdi-chevron-up',
    'icon-alt': 'mdi-chevron-down',
    text: 'Composition',
    model: false,
    link: '',
    children: [
      {
        icon: 'mdi-content-copy',
        text: 'reactive',
        link: '/sample/composition/reactive'
      },
      {
        icon: 'mdi-content-copy',
        text: 'computed',
        link: '/sample/composition/computed'
      },
      {
        icon: 'mdi-content-copy',
        text: 'props',
        link: '/sample/composition/propsParent'
      },
      {
        icon: 'mdi-content-copy',
        text: 'emits',
        link: '/sample/composition/emitsParent'
      }
    ]
  },
  {
    icon: 'mdi-chevron-up',
    'icon-alt': 'mdi-chevron-down',
    text: 'More',
    model: false,
    link: '',
    children: [
      { icon: 'mdi-plus', text: 'Import', link: '' },
      { icon: 'mdi-plus', text: 'Export', link: '' },
      { icon: 'mdi-plus', text: 'Print', link: '' },
      {
        icon: 'mdi-plus',
        text: 'Undo changes',
        link: ''
      },
      {
        icon: 'mdi-plus',
        text: 'Other contacts',
        link: ''
      }
    ]
  },
  { icon: 'mdi-cog', text: 'Settings', link: '' },
  {
    icon: 'mdi-message',
    text: 'Send feedback',
    link: ''
  },
  { icon: 'mdi-help-circle', text: 'Help', link: '' }
]);

function clickGotoLink(link: string) {
  console.log('clickGotoLink ' + link);
  void router.push({
    path: link
    // query: { ...route.query }
  });
  // if (link !== '' && this.$route.path !== link) {
  //   this.$router.push(link);
  // }
}
</script>

<script lang="ts">
export default {
  name: 'navigationLayout',
  inheritAttrs: false,
  customOptions: {}
};
</script>
