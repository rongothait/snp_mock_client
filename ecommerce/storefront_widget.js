export function onCheckoutComplete(customer) {
  console.log("order placed", customer.orderId);
  console.log(customer.email);
  console.log(customer);
}
