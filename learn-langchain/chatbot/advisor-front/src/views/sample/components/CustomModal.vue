<script setup lang="ts">
import { ref, watch, nextTick, type PropType } from 'vue';
import { getRandomId } from '@/utils';
import { useActiveElement } from '@vueuse/core';
import { useCommonStore } from '@/service/locale copy/commonModule';
import { onUnmounted } from 'vue';

export type modalType = 'alert' | 'confirm' | 'bottom' | 'full' | 'notification';
export interface modalFooterType {
  name: 'close' | 'ok';
  label: String;
  click?: Function;
  disabled?: Boolean;
}
const props = defineProps({
  /**
   * Modal Type<br>
   * type='alert' | 'confirm' | 'bottom' | 'full' | 'notification'
   */
  type: {
    type: String as PropType<modalType>,
    default: 'alert',
    require: true
  },
  /**
   * Modal Show, Hide <br>
   * v-model="modelName"
   */
  modelValue: {
    type: Boolean,
    default: false
  },
  /**
   * Hidden Header
   */
  hideHeader: {
    type: Boolean,
    default: false
  },
  /**
   * Hidden Footer
   */
  hideFooter: {
    type: Boolean,
    default: false
  },
  /**
   * Header Title Text
   */
  title: {
    type: String,
    default: 'Modal title'
  },
  /**
     * Footer Buttons <br>
     * :footer="[ <br>
          { name: 'close' | 'ok', label: String, click?: Function, disabled?: Boolean }, <br>
        ]"
     */
  footer: {
    type: Array<modalFooterType> || undefined,
    default: []
  },
  renderedCloseModal: Function as PropType<() => void>
});

const emit = defineEmits([
  /**
   * Update v-model Value
   */
  'update:modelValue',
  /**
   * Close Button Event
   */
  'close',
  /**
   * OK Button Event
   */
  'ok',
  /**
   * Open Event
   */
  'open'
]);
const randomString = getRandomId();
const modalContent = ref<HTMLDivElement | undefined>();
const activator = ref<HTMLButtonElement | undefined>();
const activeElement = useActiveElement();
const activeEl = ref<HTMLElement | null | undefined>();
const modal = ref();
// const arrayId = ref<string[]>([])
const commonStore = useCommonStore();

watch(activeElement, (el) => {
  activeEl.value = el;
});

const isShowModal = ref(false);
const modalId = `${randomString}Modal`;
// 모달 상태를 감시하여 상태를 store에 추가/제거
watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue) {
      // show 모달 정보 store에 추가
      if (!commonStore.getShowedModals.some((modal) => modal.modalId === modalId)) {
        const showedModal = {
          modalId: modalId
        };
        commonStore.pushShowedModal(showedModal);
      }
    } else {
      // show 모달 정보 store에서 제거
      commonStore.removeShowedModal(modalId);
    }
    isShowModal.value = newValue;
  },
  { immediate: true }
);

onUnmounted(() => {
  // show 모달 정보 store에서 제거. 화면이동을 통해서 모달을 닫지 못하고 이동할경우 store에서 제거
  commonStore.removeShowedModal(modalId);
});

// commonStore.getShowedModal 배열의 변경을 감시. 배열에 modalId가 없으면 closeModal 메소드를 호출. 외부(브릿지)에서 모달을 닫을때 사용.)
watch(
  () => commonStore.getShowedModals,
  () => {
    console.log('watch commonStore.getShowedModals ', commonStore.getShowedModals);
    if (
      isShowModal.value == true &&
      props.modelValue == true &&
      !commonStore.getShowedModals.some((modal) => modal.modalId === modalId)
    ) {
      closeModal();
    }
  },
  { deep: true }
);

const showModal = (e: Event) => {
  activator.value = e.target as HTMLButtonElement;
  emit('open');
  emit('update:modelValue', true);
  document.body.classList.add('modal-open');

  // a11y
  nextTick(() => {
    if (modalContent.value !== undefined) {
      modalContent.value.focus();
    }
  });
};
const closeModal = () => {
  if (props.renderedCloseModal) {
    props.renderedCloseModal();
    return;
  }
  emit('close');
  emit('update:modelValue', false);
  // modal + modal 일때 닫아도 .modal-open 넣기
  document.body.classList.remove('modal-open');
  if (document.querySelectorAll('.modal.is-open').length > 1) {
    document.body.classList.add('modal-open');
  }
  // a11y
  activator.value?.focus();
};
const okModal = () => {
  emit('ok');
  emit('update:modelValue', false);
  // modal + modal 일때 닫아도 .modal-open 넣기
  document.body.classList.remove('modal-open');
  if (document.querySelectorAll('.modal.is-open').length > 1) {
    document.body.classList.add('modal-open');
  }
  // a11y
  activator.value?.focus();
};
const focusLoop = (e: KeyboardEvent) => {
  // a11y
  if (modalContent.value !== undefined) {
    const focusEls = modalContent.value.querySelectorAll(
      'a[href], area[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), iframe, object, embed, *[tabindex], *[contenteditable]'
    );
    const firstEl = focusEls[0] as HTMLElement;
    const lastEl = focusEls[focusEls?.length - 1] as HTMLElement;
    const isTab = e.key === 'Tab' || e.keyCode === 9;
    const isEsc = e.key === 'Escape' || e.keyCode === 27;
    if (!isTab) {
      if (isEsc) {
        closeModal();
      }
      return;
    }
    if (e.shiftKey) {
      // shift + tab
      if (activeEl.value === firstEl) {
        lastEl.focus();
        e.preventDefault();
      }
    } else {
      // tab
      if (activeEl.value === lastEl) {
        firstEl.focus();
        e.preventDefault();
      }
    }
  }
};

defineExpose({
  showModal,
  closeModal
});
</script>
<template>
  <Teleport to="body">
    <Transition :name="`modal-${props.type}`">
      <div
        v-show="modelValue"
        :id="`${randomString}Modal`"
        ref="modal"
        class="modal"
        :class="[type, { 'is-open': modelValue }]"
        :role="props.type === 'alert' || props.type === 'notification' ? 'alertdialog' : 'dialog'"
        :aria-modal="true"
        :aria-labelledby="`${randomString}Title`"
        :aria-describedby="`${randomString}Desc`"
        :aria-hidden="!modelValue"
      >
        <div class="modal-dialog" @click.self="closeModal">
          <div ref="modalContent" class="modal-content" :tabindex="0" @keydown.stop="focusLoop($event)">
            <div class="modal-header" :class="{ 'is-hide': hideHeader }">
              <h3 :id="`${randomString}Title`" class="modal-title">
                <slot name="modal-header">
                  {{ props.title }}
                </slot>
              </h3>
              <button type="button" class="btn btn-close" aria-label="팝업 닫기" @click="closeModal">
                <i class="icon icon-28-close" :aria-hidden="true" />
              </button>
            </div>
            <div :id="`${randomString}Desc`" class="modal-body">
              <slot v-if="$slots.default"> modal-body </slot>
              <slot v-else name="modal-body"> modal-body </slot>
            </div>
            <div v-if="!hideFooter" class="modal-footer">
              <div class="btn-area">
                <slot name="modal-footer" :close="closeModal" :ok="okModal">
                  <template v-if="props.footer">
                    <button
                      v-for="(btn, index) in props.footer"
                      :key="index"
                      type="button"
                      :class="`btn btn-${btn.name === 'ok' ? 'primary' : 'secondary'}`"
                      :disabled="btn.disabled ? true : false"
                      @click="[btn.name === 'ok' ? okModal() : closeModal(), btn.click !== undefined && btn.click()]"
                    >
                      <span>{{ btn.label }}</span>
                    </button>
                  </template>
                  <template v-else>
                    <button type="button" class="btn btn-secondary" @click="closeModal">
                      <span>취소</span>
                    </button>
                    <button type="button" class="btn btn-primary" @click="okModal">
                      <span>확인</span>
                    </button>
                  </template>
                </slot>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style></style>
