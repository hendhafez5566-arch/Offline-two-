/* Permission facade for presentation/domain code: the only way outside security/bootstrap to ask can/require.
   Pure delegation - same arguments, same defaults, same thrown errors as Auth.can / Auth.require.
   Leaf module (no imports): security/auth.ts registers the real Auth on evaluation, so nothing changes in module evaluation order. */
interface AccessUser {id?:string;name?:string;role?:string;mustChangePassword?:boolean;onboardingSeen?:boolean;onboardingSeenAt?:string;viewCosts?:boolean;permissions?:Record<string,unknown>;maxDiscountPct?:number;branchId?:string;allowedBranchIds?:string[]}
type Provider={user?:AccessUser;can(page:string,action?:string):boolean;require(page:string,action?:string):void};
let provider:Provider|null=null;
const AccessControl={
 bind(p:Provider){provider=p},
 /* live read of the signed-in user (Auth.user is reassigned on login/logout, so never cache it) */
 currentUser():AccessUser|undefined{return provider?.user},
 /* re-bind the signed-in user to a fresher record (same user, e.g. after a server refresh) */
 setCurrentUser(user:AccessUser|undefined){if(provider)provider.user=user},
 canViewCosts(){const u=this.currentUser();return !!u && (u.role==='admin'||u.permissions?.all===true||u.viewCosts!==false)},
 requireCosts(){if(!this.canViewCosts())throw new Error('غير مسموح مشاهدة التكلفة والربحية')},
 canReadRecord(record:any,page=''){if(!this.can(page||'invoices'))return false;if(this.canViewCosts())return true;return !(record?.kind==='supplier'||record?.partyType==='supplier'||['purchaseorders','suppliers','payments','expenses'].includes(page)||['purchaseOrder','payment','expense','supplierSettlement'].includes(record?.type))},
 can(page:string,action:string='view'){if(!this.canViewCosts()&&['suppliers','purchaseorders','payments','expenses'].includes(page))return false;return provider!.can(page,action)},
 require(page:string,action:string='view'){if(!this.canViewCosts()&&['suppliers','purchaseorders','payments','expenses'].includes(page))this.requireCosts();return provider!.require(page,action)}
};
export { AccessControl };
