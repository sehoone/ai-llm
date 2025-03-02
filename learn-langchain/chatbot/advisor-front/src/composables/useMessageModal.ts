// import { ref, createApp, h, type ComponentPublicInstance, type Ref } from 'vue';
// // import { type modalFooterType, type modalType } from '@/components/uu-components/uuModal.vue';
// import uuModal from '@/components/uu-components/uuModal.vue';

// type modalType = 'alert' | 'confirm' | 'bottom' | 'full' | 'notification';
// interface modalFooterType {
//   name: 'close' | 'ok';
//   label: String;
//   click?: Function;
//   disabled?: Boolean;
// }
// interface uuModalProps {
//   type?: modalType; // Modal Type
//   modelValue?: Boolean; // Modal Show or Hide
//   hideHeader?: Boolean; // Hidden Header
//   hideFooter?: Boolean; // Hidden Footer
//   title?: string; // Modal Title
//   footer?: Array<modalFooterType>; // Footer Button
// }

// function createModalOptions(options: uuModalProps, modalType: string) {
//   const option = {
//     type: modalType || options.type || 'alert',
//     modelValue: options.modelValue || true,
//     hideHeader: options.hideHeader || false,
//     hideFooter: options.hideFooter || false,
//     title: options.title || '',
//     footer: options.footer || []
//   };
//   return option;
// }

// export function useMessageModal() {
//   const modalInstance: Ref<ComponentPublicInstance | null> = ref(null);
//   let app: any;

//   // TODO modal type별로 create추가
//   const createSuccessModal = (options: uuModalProps, content: string) => {
//     renderedShowModal(createModalOptions(options, 'notification'), content);
//   };
//   const createErrorModal = (options: uuModalProps, content: string) => {
//     renderedShowModal(createModalOptions(options, 'alert'), content);
//   };

//   const renderedShowModal = (props = {}, constent: string) => {
//     const div = document.createElement('div');
//     document.body.appendChild(div);
//     app = createApp({
//       render: () =>
//         h(
//           uuModal,
//           {
//             ...props,
//             renderedCloseModal
//           },
//           {
//             'modal-body': () => constent
//           }
//         )
//     });

//     modalInstance.value = app.mount(div);
//   };

//   const renderedCloseModal = () => {
//     if (modalInstance.value) {
//       app.unmount();
//       modalInstance.value = null;
//     }
//   };

//   return { renderedShowModal, renderedCloseModal, createErrorModal, createSuccessModal };
// }
